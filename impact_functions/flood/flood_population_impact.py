import numpy
from numpy import nansum as sum
from impact_functions.core import FunctionProvider
from impact_functions.core import get_hazard_layer, get_exposure_layers
from impact_functions.styles import flood_population_style as style_info
from storage.raster import Raster


class FloodImpactFunction(FunctionProvider):
    """Risk plugin for flood impact

    :author HKV
    :rating 1
    :param requires category=='hazard' and \
                    subcategory.startswith('flood') and \
                    layertype=='raster' and \
                    unit=='m'

    :param requires category=='exposure' and \
                    subcategory=='population' and \
                    layertype=='raster' and \
                    datatype=='density'
    """

    plugin_name = 'Terdampak'

    def run(self, layers):
        """Risk plugin for earthquake fatalities

        Input
          layers: List of layers expected to contain
              H: Raster layer of flood depth
              P: Raster layer of population data on the same grid as H
        """

        # Depth above which people are regarded affected [m]
        threshold = 0.1  # Threshold [m]

        # Identify hazard and exposure layers
        inundation = get_hazard_layer(layers)  # Flood inundation [m]

        # Get population and gender ratio
        population = gender_ratio = None
        for layer in get_exposure_layers(layers):
            keywords = layer.get_keywords()

            if 'datatype' not in keywords:
                population = layer
            else:
                datatype = keywords['datatype']

                if 'ratio' not in datatype:
                    population = layer
                else:
                    #if 'female' in datatype and 'ratio' in datatype:
                    gender_ratio_unit = keywords['unit']

                    msg = ('Unit for gender ratio must be either '
                           '"percent" or "ratio"')
                    if gender_ratio_unit not in ['percent', 'ratio']:
                        raise RuntimeError(msg)

                    gender_ratio = layer

        msg = 'No population layer was found in: %s' % str(layers)
        if population is None:
            raise RuntimeError(msg)

        # Extract data as numeric arrays
        D = inundation.get_data(nan=0.0)  # Depth

        # Calculate impact as population exposed to depths > threshold
        if population.get_resolution(native=True, isotropic=True) < 0.0005:
            # Keep this for backwards compatibility just a little while
            # This uses the original custom population set and
            # serves as a reference

            P = population.get_data(nan=0.0)  # Population density
            pixel_area = 2500
            I = numpy.where(D > threshold, P, 0) / 100000.0 * pixel_area
        else:
            # This is the new generic way of scaling (issue #168 and #172)
            P = population.get_data(nan=0.0, scaling=True)
            I = numpy.where(D > threshold, P, 0)

        if gender_ratio is not None:
            # Extract gender ratio at each pixel (as ratio)
            G = gender_ratio.get_data(nan=0.0)
            if gender_ratio_unit == 'percent':
                G /= 100

            # Calculate breakdown
            P_female = P * G
            P_male = P - P_female

            I_female = I * G
            I_male = I - I_female

        # Generate text with result for this study
        total = str(int(numpy.sum(P) / 1000))
        count = str(int(numpy.sum(I) / 1000))

        # Create report
        iname = inundation.get_name()
        pname = population.get_name()
        impact_summary = ('<table class="table table-striped condensed">')
        impact_summary += ('<caption>Apabila terjadi "%s" '
                    'perkiraan dampak terhadap "%s" '
                    'kemungkinan yang terjadi&#58;</caption>' % (iname,
                                                                     pname))
        #           '   <tr><td><b>%s&#58;</b></td>'
        #           '<td align="right"><b>%s</b></td></tr>'
        #           % ('Jumlah Penduduk', total))
        # if gender_ratio is not None:
        #     total_female = str(int(sum(P_female.flat) / 1000))
        #     total_male = str(int(sum(P_male.flat) / 1000))

        #     impact_summary += ('        <tr><td>%s&#58;</td>'
        #                 '<td align="right">%s</td></tr>'
        #                 % (' - Wanita', total_female))
        #     impact_summary += ('        <tr><td>%s&#58;</td>'
        #                 '<td align="right">%s</td></tr>'
        #                 % (' - Pria', total_male))
        #    impact_summary += '<tr><td>&nbsp;</td></tr>'  # Blank separation row
        impact_summary += ('<tbody>')
        impact_summary += ('   <tr><th>%s&#58;</th>'
                    '<td align="right">%s</td></tr>'
                    % ('Terdampak (x 1000)', count))

        if gender_ratio is not None:
            affected_female = str(int(numpy.sum(I_female) / 1000))
            affected_male = str(int(numpy.sum(I_male) / 1000))

            impact_summary += ('        <tr><th>%s&#58;</th>'
                        '<td align="right">%s</td></tr>'
                        % (' - Wanita', affected_female))
            impact_summary += ('        <tr><th>%s&#58;</th>'
                        '<td align="right">%s</td></tr>'
                        % (' - Pria', affected_male))
        impact_summary += ('</tbody>')
        impact_summary += '</table>'

        impact_summary += '<br>'  # Blank separation row
        impact_summary += '<span class="label success">Catatan&#58;</span>'
        impact_summary += '<ul>'
        impact_summary += '  <li>Jumlah penduduk Jakarta %s</li>' % total
        impact_summary += '  <li>Jumlah dalam ribuan</li>'
        impact_summary += (' <li>Penduduk dianggap terdampak ketika '
                    'banjir lebih dari %.1f m.</li>' % threshold)
        impact_summary += '</ul>'

        impact_table = ('<table class="table table-striped condensed">'
                 '  <caption>Jumlah Penduduk Yang Mungkin Dieakuasi</caption>'
                 '  <thead>'
                 '    <tr>'
                 '      <th rowspan="2">Wilayah</th>'
                 '      <th colspan="2">Jumlah Penduduk</th>'
                 '      <th rowspan="2" colspan="2" width="100px">'
                            'Jumlah Penduduk yang Mungkin dievakuasi</th>'
                 '    </tr>'
                 '    <tr>'
                 '      <th>Perempuan</th>'
                 '      <th>Laki-Laki</th>'
                 '    </tr>'
                 '  </thead>'
                 '  <tbody>'
                 '    <tr>'
                 '      <td>Jakarta Barat</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '    <tr>'
                 '      <td>Jakarta Pusat</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '    <tr>'
                 '      <td>Jakarta Seletan</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '    <tr>'
                 '      <td>Jakarta Timur</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '    <tr>'
                 '      <td>Jakarta Utara</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '    <tr>'
                 '      <td class="align-right">Total</td>'
                 '      <td>87510</td>'
                 '      <td>93076</td>'
                 '      <td>180586</td>'
                 '    </tr>'
                 '  </tbody>'
                 '  <caption>Sumber: Badan Pusat Statistik</caption>'
                 '</table>')
        map_title = 'Penduduk yang Mungkin dievakuasi'

        style_info['legend_title'] = 'Kepadatan Penduduk'
        # Create raster object and return
        R = Raster(I,
                   projection=inundation.get_projection(),
                   geotransform=inundation.get_geotransform(),
                   name='Penduduk yang %s' % (self.plugin_name.lower()),
                   keywords={'impact_summary': impact_summary,
                             'impact_table': impact_table,
                             'map_title': map_title},
                   style_info=style_info)
        return R
