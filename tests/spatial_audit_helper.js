let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let pngjs = require("pngjs");

{
  let PATHS = {
    cshapes: "F:/Active Projects/Project 1509 - SVEA/saves/CShapes-2.0.geojson",
    geocodes_csv: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/admin_modern/geocodes.csv",
    geocodes_png: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/admin_modern/geocodes.png",
    ghs_pop_2000: "F:/Active Projects/Project 1509 - SVEA/histmap/2.data_cleaning/population_GHSL/cleaned_rasters/GHS_POP_2000.png",
    ghs_pop_2020: "F:/Active Projects/Project 1509 - SVEA/histmap/2.data_cleaning/population_GHSL/cleaned_rasters/GHS_POP_2020.png",
    ghs_pop_2025: "F:/Active Projects/Project 1509 - SVEA/histmap/2.data_cleaning/population_GHSL/cleaned_rasters/GHS_POP_2025.png",
    ghsl_json: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_Stadester/ghsl/ghsl.json",
    iso2_geocodes: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/admin_modern/iso2_geocodes.csv",
    iso2_png: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/admin_modern/iso2.png",
    land_area: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png",
    ne_countries: "F:/Active Projects/Project 1436 - Dataview/public/data/ne_50m_admin_0_countries.geojson",
    populstat_cities: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_Stadester/populstat_cities/populstat_cities.json",
    populstat_countries: "F:/Active Projects/Project 1509 - SVEA/common/stadester/populstat_countries.json5",
    populstat_shards: "F:/Active Projects/Project 1509 - SVEA/tests/populstat_shards.json",
    ucdb_csv: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_GHSL/GHS_UCDB_MTUC_GLOBE_R2024A.csv",
    ucdb_markers: "F:/Active Projects/Project 1509 - SVEA/histmap/1.data_raw/population_GHSL/geojson/GHS_urban_markers.geojson"
  };

  // All 50 US states (AL..WY) + DC bounding boxes and approximate geographic centroids
  let US_STATE_BOUNDS = {
    AK: { name: "Alaska", min_lat: 51.1, max_lat: 71.6, min_lng: -179.9, max_lng: -129.8, wrap_pos_lng_min: 172.0, centroid: [64.2008, -149.4937] },
    AL: { name: "Alabama", min_lat: 30.1, max_lat: 35.1, min_lng: -88.5, max_lng: -84.8, centroid: [32.3182, -86.9023] },
    AR: { name: "Arkansas", min_lat: 33.0, max_lat: 36.6, min_lng: -94.7, max_lng: -89.6, centroid: [35.2010, -91.8318] },
    AZ: { name: "Arizona", min_lat: 31.3, max_lat: 37.1, min_lng: -114.9, max_lng: -109.0, centroid: [34.0489, -111.0937] },
    CA: { name: "California", min_lat: 32.5, max_lat: 42.1, min_lng: -124.5, max_lng: -114.1, centroid: [36.7783, -119.4179] },
    CO: { name: "Colorado", min_lat: 36.9, max_lat: 41.1, min_lng: -109.1, max_lng: -102.0, centroid: [39.5501, -105.7821] },
    CT: { name: "Connecticut", min_lat: 40.9, max_lat: 42.1, min_lng: -73.8, max_lng: -71.7, centroid: [41.6032, -73.0877] },
    DC: { name: "District of Columbia", min_lat: 38.75, max_lat: 39.05, min_lng: -77.15, max_lng: -76.85, centroid: [38.9072, -77.0369] },
    DE: { name: "Delaware", min_lat: 38.4, max_lat: 39.9, min_lng: -75.85, max_lng: -75.0, centroid: [38.9108, -75.5277] },
    FL: { name: "Florida", min_lat: 24.4, max_lat: 31.1, min_lng: -87.7, max_lng: -79.9, centroid: [27.6648, -81.5158] },
    GA: { name: "Georgia", min_lat: 30.3, max_lat: 35.1, min_lng: -85.7, max_lng: -80.7, centroid: [32.1656, -82.9001] },
    HI: { name: "Hawaii", min_lat: 18.8, max_lat: 22.3, min_lng: -160.4, max_lng: -154.7, centroid: [19.8968, -155.5828] },
    IA: { name: "Iowa", min_lat: 40.3, max_lat: 43.6, min_lng: -96.7, max_lng: -90.1, centroid: [41.8780, -93.0977] },
    ID: { name: "Idaho", min_lat: 41.9, max_lat: 49.1, min_lng: -117.3, max_lng: -111.0, centroid: [44.0682, -114.7420] },
    IL: { name: "Illinois", min_lat: 36.9, max_lat: 42.6, min_lng: -91.6, max_lng: -87.4, centroid: [40.6331, -89.3985] },
    IN: { name: "Indiana", min_lat: 37.7, max_lat: 41.8, min_lng: -88.2, max_lng: -84.7, centroid: [40.2672, -86.1349] },
    KS: { name: "Kansas", min_lat: 36.9, max_lat: 40.1, min_lng: -102.1, max_lng: -94.5, centroid: [39.0119, -98.4842] },
    KY: { name: "Kentucky", min_lat: 36.4, max_lat: 39.2, min_lng: -89.6, max_lng: -81.9, centroid: [37.8393, -84.2700] },
    LA: { name: "Louisiana", min_lat: 28.9, max_lat: 33.1, min_lng: -94.1, max_lng: -88.8, centroid: [30.9843, -91.9623] },
    MA: { name: "Massachusetts", min_lat: 41.2, max_lat: 42.95, min_lng: -73.6, max_lng: -69.85, centroid: [42.4072, -71.3824] },
    MD: { name: "Maryland", min_lat: 37.8, max_lat: 39.8, min_lng: -79.55, max_lng: -75.0, centroid: [39.0458, -76.6413] },
    ME: { name: "Maine", min_lat: 43.0, max_lat: 47.5, min_lng: -71.15, max_lng: -66.85, centroid: [45.2538, -69.4455] },
    MI: { name: "Michigan", min_lat: 41.65, max_lat: 48.3, min_lng: -90.5, max_lng: -82.3, centroid: [44.3148, -85.6024] },
    MN: { name: "Minnesota", min_lat: 43.45, max_lat: 49.45, min_lng: -97.3, max_lng: -89.4, centroid: [46.7296, -94.6859] },
    MO: { name: "Missouri", min_lat: 35.95, max_lat: 40.65, min_lng: -95.8, max_lng: -89.05, centroid: [37.9643, -91.8318] },
    MS: { name: "Mississippi", min_lat: 30.1, max_lat: 35.05, min_lng: -91.7, max_lng: -88.05, centroid: [32.3547, -89.3985] },
    MT: { name: "Montana", min_lat: 44.3, max_lat: 49.05, min_lng: -116.1, max_lng: -104.0, centroid: [46.8797, -110.3626] },
    NC: { name: "North Carolina", min_lat: 33.8, max_lat: 36.65, min_lng: -84.4, max_lng: -75.4, centroid: [35.7596, -79.0193] },
    ND: { name: "North Dakota", min_lat: 45.9, max_lat: 49.05, min_lng: -104.1, max_lng: -96.5, centroid: [47.5515, -101.0020] },
    NE: { name: "Nebraska", min_lat: 39.95, max_lat: 43.05, min_lng: -104.1, max_lng: -95.25, centroid: [41.4925, -99.9018] },
    NH: { name: "New Hampshire", min_lat: 42.65, max_lat: 45.35, min_lng: -72.6, max_lng: -70.6, centroid: [43.1939, -71.5724] },
    NJ: { name: "New Jersey", min_lat: 38.9, max_lat: 41.4, min_lng: -75.6, max_lng: -73.85, centroid: [40.0583, -74.4057] },
    NM: { name: "New Mexico", min_lat: 31.3, max_lat: 37.05, min_lng: -109.1, max_lng: -102.95, centroid: [34.5199, -105.8701] },
    NV: { name: "Nevada", min_lat: 35.0, max_lat: 42.05, min_lng: -120.05, max_lng: -114.0, centroid: [38.8026, -116.4194] },
    NY: { name: "New York", min_lat: 40.45, max_lat: 45.05, min_lng: -79.8, max_lng: -71.8, centroid: [43.2994, -74.2179] },
    OH: { name: "Ohio", min_lat: 38.35, max_lat: 42.0, min_lng: -84.85, max_lng: -80.45, centroid: [40.4173, -82.9071] },
    OK: { name: "Oklahoma", min_lat: 33.6, max_lat: 37.05, min_lng: -103.05, max_lng: -94.4, centroid: [35.0078, -97.0929] },
    OR: { name: "Oregon", min_lat: 41.95, max_lat: 46.35, min_lng: -124.65, max_lng: -116.4, centroid: [43.8041, -120.5542] },
    PA: { name: "Pennsylvania", min_lat: 39.65, max_lat: 42.3, min_lng: -80.55, max_lng: -74.65, centroid: [41.2033, -77.1945] },
    RI: { name: "Rhode Island", min_lat: 41.1, max_lat: 42.05, min_lng: -71.95, max_lng: -71.05, centroid: [41.5801, -71.4774] },
    SC: { name: "South Carolina", min_lat: 32.0, max_lat: 35.25, min_lng: -83.4, max_lng: -78.5, centroid: [33.8361, -81.1637] },
    SD: { name: "South Dakota", min_lat: 42.45, max_lat: 45.95, min_lng: -104.1, max_lng: -96.4, centroid: [43.9695, -99.9018] },
    TN: { name: "Tennessee", min_lat: 34.95, max_lat: 36.7, min_lng: -90.35, max_lng: -81.6, centroid: [35.5175, -86.5804] },
    TX: { name: "Texas", min_lat: 25.8, max_lat: 36.55, min_lng: -106.7, max_lng: -93.45, centroid: [31.9686, -99.9018] },
    UT: { name: "Utah", min_lat: 36.95, max_lat: 42.05, min_lng: -114.1, max_lng: -109.0, centroid: [39.3210, -111.0937] },
    VA: { name: "Virginia", min_lat: 36.5, max_lat: 39.5, min_lng: -83.7, max_lng: -75.2, centroid: [37.4316, -78.6569] },
    VT: { name: "Vermont", min_lat: 42.7, max_lat: 45.05, min_lng: -73.45, max_lng: -71.45, centroid: [44.5588, -72.5778] },
    WA: { name: "Washington", min_lat: 45.5, max_lat: 49.05, min_lng: -124.85, max_lng: -116.85, centroid: [47.7511, -120.7401] },
    WI: { name: "Wisconsin", min_lat: 42.45, max_lat: 47.1, min_lng: -92.95, max_lng: -86.75, centroid: [43.7844, -88.7879] },
    WV: { name: "West Virginia", min_lat: 37.15, max_lat: 40.65, min_lng: -82.65, max_lng: -77.7, centroid: [38.5976, -80.4549] },
    WY: { name: "Wyoming", min_lat: 40.95, max_lat: 45.05, min_lng: -111.1, max_lng: -104.0, centroid: [43.0760, -107.2903] }
  };

  // Island/microstate/archipelago bounding boxes (min_lng > max_lng implies antimeridian wrap)
  let ARCHIPELAGO_BOUNDS = {
    "American Samoa": [{ min_lat: -14.7, max_lat: -11.0, min_lng: -171.3, max_lng: -168.0 }],
    Andorra: [{ min_lat: 42.4, max_lat: 42.7, min_lng: 1.4, max_lng: 1.85 }],
    Anguilla: [{ min_lat: 18.1, max_lat: 18.35, min_lng: -63.25, max_lng: -62.9 }],
    "Antigua and Barbuda": [{ min_lat: 16.9, max_lat: 17.8, min_lng: -62.0, max_lng: -61.6 }],
    Aruba: [{ min_lat: 12.35, max_lat: 12.7, min_lng: -70.15, max_lng: -69.8 }],
    Bahrain: [{ min_lat: 25.55, max_lat: 26.35, min_lng: 50.35, max_lng: 50.85 }],
    Barbados: [{ min_lat: 13.0, max_lat: 13.4, min_lng: -59.7, max_lng: -59.35 }],
    Bermuda: [{ min_lat: 32.2, max_lat: 32.45, min_lng: -64.95, max_lng: -64.6 }],
    "British Virgin Islands": [{ min_lat: 18.3, max_lat: 18.8, min_lng: -64.85, max_lng: -64.2 }],
    "Cape Verde": [{ min_lat: 14.7, max_lat: 17.3, min_lng: -25.45, max_lng: -22.6 }],
    "Cayman Islands": [{ min_lat: 19.2, max_lat: 19.8, min_lng: -81.5, max_lng: -79.7 }],
    Comoros: [{ min_lat: -12.5, max_lat: -11.3, min_lng: 43.1, max_lng: 44.6 }],
    "Cook Islands": [{ min_lat: -22.2, max_lat: -8.8, min_lng: -166.1, max_lng: -157.2 }],
    Dominica: [{ min_lat: 15.15, max_lat: 15.7, min_lng: -61.55, max_lng: -61.2 }],
    "Falkland Islands": [{ min_lat: -52.6, max_lat: -51.0, min_lng: -61.5, max_lng: -57.6 }],
    "Faroe Islands": [{ min_lat: 61.35, max_lat: 62.45, min_lng: -7.75, max_lng: -6.2 }],
    Fiji: [{ min_lat: -21.1, max_lat: -12.3, min_lng: 176.7, max_lng: -178.0 }],
    "French Polynesia": [{ min_lat: -28.0, max_lat: -7.8, min_lng: -155.0, max_lng: -134.0 }],
    Grenada: [{ min_lat: 11.95, max_lat: 12.55, min_lng: -61.85, max_lng: -61.3 }],
    Guadeloupe: [{ min_lat: 15.8, max_lat: 18.15, min_lng: -63.15, max_lng: -60.95 }],
    Guam: [{ min_lat: 13.2, max_lat: 13.7, min_lng: 144.6, max_lng: 145.0 }],
    "Hong Kong": [{ min_lat: 22.12, max_lat: 22.6, min_lng: 113.8, max_lng: 114.48 }],
    Kiribati: [
      { name: "Gilbert Islands", min_lat: -3.0, max_lat: 3.5, min_lng: 169.4, max_lng: 177.2 },
      { name: "Phoenix Islands", min_lat: -5.0, max_lat: -2.4, min_lng: -174.9, max_lng: -170.4 },
      { name: "Line Islands", min_lat: -11.6, max_lat: 5.0, min_lng: -160.8, max_lng: -150.0 }
    ],
    Maldives: [{ min_lat: -0.8, max_lat: 7.2, min_lng: 72.5, max_lng: 73.9 }],
    Malta: [{ min_lat: 35.78, max_lat: 36.12, min_lng: 14.15, max_lng: 14.6 }],
    "Marshall Islands": [{ min_lat: 4.4, max_lat: 14.8, min_lng: 160.5, max_lng: 172.5 }],
    Martinique: [{ min_lat: 14.35, max_lat: 14.95, min_lng: -61.3, max_lng: -60.75 }],
    Mauritius: [{ min_lat: -20.6, max_lat: -10.3, min_lng: 56.4, max_lng: 63.6 }],
    Mayotte: [{ min_lat: -13.1, max_lat: -12.6, min_lng: 44.95, max_lng: 45.35 }],
    Micronesia: [{ min_lat: 0.9, max_lat: 10.2, min_lng: 137.3, max_lng: 163.2 }],
    Monaco: [{ min_lat: 43.71, max_lat: 43.76, min_lng: 7.39, max_lng: 7.45 }],
    Montserrat: [{ min_lat: 16.65, max_lat: 16.85, min_lng: -62.28, max_lng: -62.12 }],
    Nauru: [{ min_lat: -0.6, max_lat: -0.45, min_lng: 166.85, max_lng: 167.0 }],
    "Netherlands Antilles": [{ min_lat: 11.95, max_lat: 18.15, min_lng: -69.25, max_lng: -62.9 }],
    "New Caledonia": [{ min_lat: -22.85, max_lat: -19.5, min_lng: 163.5, max_lng: 168.3 }],
    Niue: [{ min_lat: -19.2, max_lat: -18.9, min_lng: -170.0, max_lng: -169.7 }],
    "Norfolk Island": [{ min_lat: -29.1, max_lat: -28.95, min_lng: 167.85, max_lng: 168.05 }],
    "Northern Mariana Islands": [{ min_lat: 14.0, max_lat: 20.6, min_lng: 144.8, max_lng: 146.2 }],
    Palau: [{ min_lat: 2.8, max_lat: 8.2, min_lng: 131.0, max_lng: 134.8 }],
    "Puerto Rico": [{ min_lat: 17.85, max_lat: 18.6, min_lng: -68.0, max_lng: -65.2 }],
    "Réunion": [{ min_lat: -21.45, max_lat: -20.8, min_lng: 55.15, max_lng: 55.9 }],
    "Saint Helena": [
      { min_lat: -16.1, max_lat: -7.8, min_lng: -14.5, max_lng: -5.6 },
      { min_lat: -40.4, max_lat: -37.0, min_lng: -12.6, max_lng: -9.8 }
    ],
    "Saint Kitts and Nevis": [{ min_lat: 17.05, max_lat: 17.45, min_lng: -62.9, max_lng: -62.5 }],
    "Saint Lucia": [{ min_lat: 13.68, max_lat: 14.15, min_lng: -61.12, max_lng: -60.85 }],
    "Saint Vincent and the Grenadines": [{ min_lat: 12.55, max_lat: 13.42, min_lng: -61.5, max_lng: -61.08 }],
    Samoa: [{ min_lat: -14.2, max_lat: -13.3, min_lng: -173.0, max_lng: -171.2 }],
    "San Marino": [{ min_lat: 43.88, max_lat: 44.0, min_lng: 12.39, max_lng: 12.52 }],
    "Sao Tome and Principe": [{ min_lat: -0.05, max_lat: 1.75, min_lng: 6.4, max_lng: 7.5 }],
    Seychelles: [{ min_lat: -10.5, max_lat: -3.6, min_lng: 46.0, max_lng: 56.4 }],
    Singapore: [{ min_lat: 1.14, max_lat: 1.49, min_lng: 103.58, max_lng: 104.1 }],
    "Solomon Islands": [{ min_lat: -12.0, max_lat: -5.0, min_lng: 155.4, max_lng: 170.3 }],
    "South Georgia and the South Sandwich Islands": [{ min_lat: -59.6, max_lat: -53.9, min_lng: -38.5, max_lng: -26.0 }],
    Svalbard: [{ min_lat: 74.3, max_lat: 80.9, min_lng: 10.0, max_lng: 33.8 }],
    "The Bahamas": [{ min_lat: 20.9, max_lat: 27.3, min_lng: -79.4, max_lng: -72.6 }],
    Tokelau: [{ min_lat: -9.5, max_lat: -8.4, min_lng: -172.6, max_lng: -171.1 }],
    Tonga: [{ min_lat: -22.6, max_lat: -15.4, min_lng: -176.5, max_lng: -173.5 }],
    "Trinidad and Tobago": [{ min_lat: 10.0, max_lat: 11.4, min_lng: -62.0, max_lng: -60.45 }],
    "Turks and Caicos Islands": [{ min_lat: 21.1, max_lat: 22.05, min_lng: -72.55, max_lng: -71.05 }],
    Tuvalu: [{ min_lat: -11.0, max_lat: -5.4, min_lng: 175.8, max_lng: 180.0 }],
    "US Virgin Islands": [{ min_lat: 17.65, max_lat: 18.45, min_lng: -65.15, max_lng: -64.5 }],
    Vanuatu: [{ min_lat: -20.4, max_lat: -13.0, min_lng: 166.4, max_lng: 170.4 }],
    "Wallis and Futuna": [{ min_lat: -14.5, max_lat: -13.1, min_lng: -178.3, max_lng: -176.0 }]
  };

  // Known Google/Nominatim country geocoder fallback coordinates (in addition to NE polygon/bbox centroids)
  let GOOGLE_CENTROIDS = {
    Afghanistan: [33.9391, 67.7100],
    Albania: [41.1533, 20.1683],
    Algeria: [28.0339, 1.6596],
    Angola: [-11.2027, 17.8739],
    Argentina: [-38.4161, -63.6167],
    Armenia: [40.0691, 45.0382],
    Australia: [-25.2744, 133.7751],
    Austria: [47.5162, 14.5501],
    Azerbaijan: [40.1431, 47.5769],
    Bangladesh: [23.6850, 90.3563],
    Belarus: [53.7098, 27.9534],
    Belgium: [50.5039, 4.4699],
    Bolivia: [-16.2902, -63.5887],
    "Bosnia and Herzegovina": [43.9159, 17.6791],
    Brazil: [-14.2350, -51.9253],
    Bulgaria: [42.7339, 25.4858],
    Cambodia: [12.5657, 104.9910],
    Cameroon: [7.3697, 12.3547],
    Canada: [56.1304, -106.3468],
    Chile: [-35.6751, -71.5430],
    China: [35.8617, 104.1954],
    Colombia: [4.5709, -74.2973],
    "Costa Rica": [9.7489, -83.7534],
    Croatia: [45.1000, 15.2000],
    Cuba: [21.5218, -77.7812],
    Cyprus: [35.1264, 33.4299],
    "Czech Republic": [49.8175, 15.4730],
    "Democratic Republic of the Congo": [-4.0383, 21.7587],
    Denmark: [56.2639, 9.5018],
    "Dominican Republic": [18.7357, -70.1627],
    Ecuador: [-1.8312, -78.1834],
    Egypt: [26.8206, 30.8025],
    "El Salvador": [13.7942, -88.8965],
    Ethiopia: [9.1450, 40.4897],
    Finland: [61.9241, 25.7482],
    France: [46.2276, 2.2137],
    Georgia: [42.3154, 43.3569],
    Germany: [51.1657, 10.4515],
    Ghana: [7.9465, -1.0232],
    Greece: [39.0742, 21.8243],
    Guatemala: [15.7835, -90.2308],
    Guyana: [4.8604, -58.9302],
    Haiti: [18.9712, -72.2852],
    Honduras: [15.2000, -86.2419],
    Hungary: [47.1625, 19.5033],
    Iceland: [64.9631, -19.0208],
    India: [20.5937, 78.9629],
    Indonesia: [-0.7893, 113.9213],
    Iran: [32.4279, 53.6880],
    Iraq: [33.2232, 43.6793],
    Ireland: [53.4129, -8.2439],
    Israel: [31.0461, 34.8516],
    Italy: [41.8719, 12.5674],
    "Ivory Coast": [7.5400, -5.5471],
    Japan: [36.2048, 138.2529],
    Jordan: [30.5852, 36.2384],
    Kazakhstan: [48.0196, 66.9237],
    Kenya: [-0.0236, 37.9062],
    Kuwait: [29.3117, 47.4818],
    Kyrgyzstan: [41.2044, 74.7661],
    Laos: [19.8563, 102.4955],
    Latvia: [56.8796, 24.6032],
    Lebanon: [33.8547, 35.8623],
    Libya: [26.3351, 17.2283],
    Lithuania: [55.1694, 23.8813],
    Madagascar: [-18.7669, 46.8691],
    Malaysia: [4.2105, 101.9758],
    Mali: [17.5707, -3.9962],
    Mexico: [23.6345, -102.5528],
    Moldova: [47.4116, 28.3699],
    Mongolia: [46.8625, 103.8467],
    Morocco: [31.7917, -7.0926],
    Mozambique: [-18.6657, 35.5296],
    Myanmar: [21.9162, 95.9560],
    Nepal: [28.3949, 84.1240],
    Netherlands: [52.1326, 5.2913],
    "New Zealand": [-40.9006, 174.8860],
    Nicaragua: [12.8654, -85.2072],
    Niger: [17.6078, 8.0817],
    Nigeria: [9.0820, 8.6753],
    "North Korea": [40.3399, 127.5101],
    "North Macedonia": [41.6086, 21.7453],
    Norway: [60.4720, 8.4689],
    Oman: [21.4735, 55.9754],
    Pakistan: [30.3753, 69.3451],
    Panama: [8.5380, -80.7821],
    "Papua New Guinea": [-6.3150, 143.9555],
    Paraguay: [-23.4425, -58.4438],
    Peru: [-9.1900, -75.0152],
    Philippines: [12.8797, 121.7740],
    Poland: [51.9194, 19.1451],
    Portugal: [39.3999, -8.2245],
    Romania: [45.9432, 24.9668],
    Russia: [61.5240, 105.3188],
    "Saudi Arabia": [23.8859, 45.0792],
    Senegal: [14.4974, -14.4524],
    Serbia: [44.0165, 21.0059],
    Slovakia: [48.6690, 19.6990],
    Slovenia: [46.1512, 14.9955],
    Somalia: [5.1521, 46.1996],
    "South Africa": [-30.5595, 22.9375],
    "South Korea": [35.9078, 127.7669],
    Spain: [40.4637, -3.7492],
    "Sri Lanka": [7.8731, 80.7718],
    Sudan: [12.8628, 30.2176],
    Sweden: [60.1282, 18.6435],
    Switzerland: [46.8182, 8.2275],
    Syria: [34.8021, 38.9968],
    Taiwan: [23.6978, 120.9605],
    Tajikistan: [38.8610, 71.2761],
    Tanzania: [-6.3690, 34.8888],
    Thailand: [15.8700, 100.9925],
    Tunisia: [33.8869, 9.5375],
    Turkey: [38.9637, 35.2433],
    Turkmenistan: [38.9697, 59.5563],
    Uganda: [1.3733, 32.2903],
    Ukraine: [48.3794, 31.1656],
    "United Arab Emirates": [23.4241, 53.8478],
    "United Kingdom": [55.3781, -3.4360],
    "United States": [37.0902, -95.7129],
    Uruguay: [-32.5228, -55.7658],
    Uzbekistan: [41.3775, 64.5853],
    Venezuela: [6.4238, -66.5897],
    Vietnam: [14.0583, 108.2772],
    Yemen: [15.5527, 48.5164],
    Zambia: [-13.1339, 27.8493],
    Zimbabwe: [-19.0154, 29.1549]
  };

  let COUNTRY_ALIASES = {
    bosnia: "Bosnia and Herzegovina",
    "bosnia herzegovina": "Bosnia and Herzegovina",
    "cabo verde": "Cape Verde",
    "central african rep.": "Central African Republic",
    "cote d'ivoire": "Ivory Coast",
    "côte d'ivoire": "Ivory Coast",
    "czech rep.": "Czech Republic",
    czechia: "Czech Republic",
    "dominican rep.": "Dominican Republic",
    "hong kong s.a.r.": "Hong Kong",
    "hong kong sar": "Hong Kong",
    luxemburg: "Luxembourg",
    "macao s.a.r": "Macau",
    "macao sar": "Macau",
    macao: "Macau",
    macedonia: "North Macedonia",
    "méxico": "Mexico",
    "republic of serbia": "Serbia",
    reunion: "Réunion",
    romenia: "Romania",
    "sao tome & principe": "Sao Tome and Principe",
    "são tomé and príncipe": "Sao Tome and Principe",
    "st. kitts and nevis": "Saint Kitts and Nevis",
    "st. vincent and the grenadines": "Saint Vincent and the Grenadines",
    swaziland: "Eswatini",
    "the netherlands": "Netherlands",
    "timor-leste": "East Timor",
    "trinidad & tobago": "Trinidad and Tobago",
    "türkiye": "Turkey",
    uae: "United Arab Emirates",
    uk: "United Kingdom",
    "united states of america": "United States",
    usa: "United States",
    ussr: "Russia",
    "viet nam": "Vietnam",
    yugoslavia: "Serbia"
  };

  // Explicit polygon allowances: primary NE ADMIN names, optional dependency NE ADMIN names, optional CShapes name
  let TERRITORY_RULES = {
    Australia: { primary: ["Australia"], dependencies: ["Indian Ocean Territories", "Norfolk Island", "Ashmore and Cartier Islands", "Heard Island and McDonald Islands"] },
    "Cape Verde": { primary: ["Cabo Verde"] },
    China: { primary: ["China", "Hong Kong S.A.R.", "Macao S.A.R"] },
    Colombia: { primary: ["Colombia"], allow_boxes: [{ name: "San Andrés y Providencia", min_lat: 12.4, max_lat: 13.5, min_lng: -81.9, max_lng: -81.2 }] },
    Congo: { primary: ["Republic of the Congo", "Democratic Republic of the Congo"] },
    Croatia: { primary: ["Croatia"], allow_boxes: [{ name: "Adriatic Islands", min_lat: 42.3, max_lat: 45.6, min_lng: 13.4, max_lng: 19.5 }] },
    Cyprus: { primary: ["Cyprus", "Northern Cyprus"] },
    "Czech Republic": { primary: ["Czechia"] },
    Denmark: { primary: ["Denmark"], dependencies: ["Greenland", "Faroe Islands"], metro_box: { min_lat: 54.4, max_lat: 57.9, min_lng: 7.9, max_lng: 15.3 } },
    Eswatini: { primary: ["eSwatini"] },
    France: {
      primary: ["France"],
      dependencies: ["French Polynesia", "New Caledonia", "Wallis and Futuna", "Saint Pierre and Miquelon", "Saint Martin", "Saint Barthelemy", "French Southern and Antarctic Lands"],
      metro_box: { min_lat: 41.2, max_lat: 51.2, min_lng: -5.3, max_lng: 9.7 }
    },
    "French Guiana": { primary: ["France"], metro_box: { min_lat: 2.0, max_lat: 6.0, min_lng: -54.8, max_lng: -51.5 } },
    Guadeloupe: { primary: ["France"], metro_box: { min_lat: 15.8, max_lat: 18.15, min_lng: -63.15, max_lng: -60.95 } },
    "Holy Land": { primary: ["Israel", "Palestine"] },
    "Hong Kong": { primary: ["Hong Kong S.A.R."] },
    Honduras: { primary: ["Honduras"], allow_boxes: [{ name: "Bay Islands", min_lat: 16.0, max_lat: 16.6, min_lng: -87.1, max_lng: -85.8 }] },
    Iceland: { primary: ["Iceland"], allow_boxes: [{ name: "Vestmannaeyjar", min_lat: 63.25, max_lat: 63.55, min_lng: -20.5, max_lng: -20.1 }] },
    India: {
      primary: ["India"],
      allow_boxes: [
        { name: "Lakshadweep", min_lat: 8.0, max_lat: 12.6, min_lng: 71.4, max_lng: 74.1 },
        { name: "Andaman and Nicobar", min_lat: 6.5, max_lat: 14.0, min_lng: 92.0, max_lng: 94.3 }
      ]
    },
    Israel: { primary: ["Israel", "Palestine"] },
    Korea: { primary: ["South Korea", "North Korea"] },
    Macau: { primary: ["Macao S.A.R"] },
    Malaysia: { primary: ["Malaysia"], allow_boxes: [{ name: "Labuan", min_lat: 5.2, max_lat: 5.4, min_lng: 115.1, max_lng: 115.35 }] },
    Martinique: { primary: ["France"], metro_box: { min_lat: 14.35, max_lat: 14.95, min_lng: -61.3, max_lng: -60.75 } },
    Mayotte: { primary: ["France"], metro_box: { min_lat: -13.1, max_lat: -12.6, min_lng: 44.95, max_lng: 45.35 } },
    Micronesia: { primary: ["Federated States of Micronesia"] },
    Morocco: { primary: ["Morocco", "Western Sahara"] },
    Netherlands: {
      primary: ["Netherlands"],
      dependencies: ["Aruba", "Curaçao", "Sint Maarten"],
      metro_box: { min_lat: 50.6, max_lat: 53.7, min_lng: 3.2, max_lng: 7.3 }
    },
    "Netherlands Antilles": { primary: ["Netherlands", "Curaçao", "Sint Maarten"] },
    "New Zealand": { primary: ["New Zealand"], dependencies: ["Cook Islands", "Niue"] },
    Norway: { primary: ["Norway"], metro_box: { min_lat: 57.8, max_lat: 71.3, min_lng: 4.3, max_lng: 31.3 } },
    Palestine: { primary: ["Palestine", "Israel"] },
    Portugal: { primary: ["Portugal"], metro_box: { min_lat: 36.8, max_lat: 42.3, min_lng: -9.6, max_lng: -6.1 }, allow_boxes: [{ min_lat: 32.5, max_lat: 33.2, min_lng: -17.3, max_lng: -16.2 }, { min_lat: 36.8, max_lat: 39.8, min_lng: -31.4, max_lng: -24.9 }] },
    "Réunion": { primary: ["France"], metro_box: { min_lat: -21.45, max_lat: -20.8, min_lng: 55.15, max_lng: 55.9 } },
    "Sao Tome and Principe": { primary: ["São Tomé and Principe"] },
    Serbia: { primary: ["Republic of Serbia", "Kosovo", "Montenegro"] },
    Somalia: { primary: ["Somalia", "Somaliland"] },
    "South Georgia and the South Sandwich Islands": { primary: ["South Georgia and the Islands"] },
    Spain: { primary: ["Spain"], metro_box: { min_lat: 35.8, max_lat: 43.9, min_lng: -9.4, max_lng: 4.5 }, allow_boxes: [{ name: "Canary Islands", min_lat: 27.5, max_lat: 29.5, min_lng: -18.5, max_lng: -13.3 }, { name: "Ceuta", min_lat: 35.86, max_lat: 35.92, min_lng: -5.36, max_lng: -5.27, ignore_foreign: true }, { name: "Melilla", min_lat: 35.26, max_lat: 35.32, min_lng: -2.97, max_lng: -2.91, ignore_foreign: true }] },
    Sudan: { primary: ["Sudan", "South Sudan"] },
    Svalbard: { primary: ["Norway"], metro_box: { min_lat: 74.3, max_lat: 80.9, min_lng: 10.0, max_lng: 33.8 } },
    Taiwan: { primary: ["Taiwan"], allow_boxes: [{ name: "Penghu/Kinmen/Matsu", min_lat: 23.1, max_lat: 26.4, min_lng: 118.1, max_lng: 120.7 }] },
    Tanzania: { primary: ["United Republic of Tanzania"] },
    "The Bahamas": { primary: ["The Bahamas"] },
    "The Gambia": { primary: ["Gambia"] },
    "US Virgin Islands": { primary: ["United States Virgin Islands"] },
    Ukraine: { primary: ["Ukraine"], cshapes_1991: "Ukraine" },
    "United Kingdom": {
      primary: ["United Kingdom", "Jersey", "Guernsey", "Isle of Man"],
      dependencies: ["Anguilla", "Bermuda", "British Indian Ocean Territory", "British Virgin Islands", "Cayman Islands", "Falkland Islands", "Montserrat", "Pitcairn Islands", "Saint Helena", "South Georgia and the Islands", "Turks and Caicos Islands"],
      allow_boxes: [{ min_lat: 36.08, max_lat: 36.17, min_lng: -5.38, max_lng: -5.32 }]
    },
    "United States": {
      primary: ["United States of America"],
      dependencies: ["American Samoa", "Guam", "Northern Mariana Islands", "Puerto Rico", "United States Virgin Islands"]
    },
    // DeVries historical regional labels
    "Austria and Czechoslovakia": { primary: ["Austria", "Czechia", "Slovakia"] },
    "Central Italy": { primary: ["Italy", "San Marino", "Vatican"] },
    "England and Wales": { primary: ["United Kingdom"] },
    "Northern Italy": { primary: ["Italy"] },
    Scandinavia: { primary: ["Denmark", "Norway", "Sweden"] },
    Scotland: { primary: ["United Kingdom"] },
    "Southern Italy": { primary: ["Italy"] }
  };

  let SUBNATIONAL_FIELDS = [
    "state", "province", "prov.", "estado", "prefecture", "préfecture",
    "region", "région", "dept.", "depto.", "dep.", "district", "parish",
    "marz", "island", "atoll", "Zila", "kraj", "amt", "maakon", "\"Land\"",
    "canton", "ostan", "county", "muhaf.", "div./state", "zone, or district",
    "municip.", "fylke", "wojw.", "municipality", "arrond.", "judet",
    "concelho", "* = Wilayat", "vilayet", "emirate", "tinh (province)"
  ];

  let POPULSTAT_DIACRITIC_MAP = {
    "`c": "c", "'c": "c", "`s": "s", "'s": "s", "`z": "z", "'z": "z",
    "`n": "n", "'n": "n", "`r": "r", "'r": "r", "`d": "d", "'d": "d",
    "`t": "t", "'t": "t", "`l": "l", "'l": "l", "~e": "e", "`e": "e"
  };

  let _cached_context = null;

  /**
   * Normalises longitude into [-180, 180).
   * @param {number} arg0_lng
   * @returns {number}
   */
  function normLng (arg0_lng) {
    let lng = Number(arg0_lng);
    if (!Number.isFinite(lng)) return 0;
    return ((lng + 180)%360 + 360)%360 - 180;
  }

  /**
   * Computes Haversine distance in km between two [lat, lng] coordinates.
   * @param {Array<number>} arg0_coords
   * @param {Array<number>} arg1_coords
   * @returns {number}
   */
  function haversineDistanceKm (arg0_coords, arg1_coords) {
    let a = arg0_coords;
    let b = arg1_coords;
    if (!a || !b || a.length < 2 || b.length < 2) return Infinity;
    let lat1 = Number(a[0])*Math.PI/180;
    let lat2 = Number(b[0])*Math.PI/180;
    let d_lat = (Number(b[0]) - Number(a[0]))*Math.PI/180;
    let d_lng = (normLng(b[1] - a[1]))*Math.PI/180;
    if (!Number.isFinite(lat1) || !Number.isFinite(lat2) || !Number.isFinite(d_lng)) return Infinity;
    let h = Math.sin(d_lat/2)*Math.sin(d_lat/2) +
      Math.sin(d_lng/2)*Math.sin(d_lng/2)*Math.cos(lat1)*Math.cos(lat2);
    return 6371*2*Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h)));
  }

  /**
   * Normalises a settlement or subdivision name, stripping Populstat backtick/tilde diacritics and urban suffixes.
   * @param {string} arg0_name
   * @returns {string}
   */
  function normaliseName (arg0_name) {
    let str = (arg0_name !== undefined && arg0_name !== null) ? String(arg0_name) : "";
    if (!str) return "";
    str = str.replace(/[`'~][csznrdtle]/gi, (m) => POPULSTAT_DIACRITIC_MAP[m.toLowerCase()] || m.slice(1));
    return str
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\([^)]*\)/g, " ")
      .replace(/\[[^\]]*\]/g, " ")
      .replace(/\b(greater|agglomeration|zona urbana|stad|agglom|urban area|cdp|grad|subtotal|city)\b/gi, " ")
      .replace(/['’`´\-_/.,]/g, " ")
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  /**
   * Parses a semicolon-delimited RFC-4180 CSV line safely (preserving semicolons inside quotes).
   * @param {string} arg0_line
   * @returns {Array<string>}
   */
  function parseSemicolonCSVLine (arg0_line) {
    let cols = [];
    let cur = "";
    let in_quotes = false;
    let line = String(arg0_line || "");
    for (let i = 0; i < line.length; i++) {
      let ch = line[i];
      if (ch === "\"") {
        if (in_quotes && i + 1 < line.length && line[i + 1] === "\"") {
          cur += "\"";
          i++;
        } else {
          in_quotes = !in_quotes;
        }
      } else if (ch === ";" && !in_quotes) {
        cols.push(cur);
        cur = "";
      } else {
        cur += ch;
      }
    }
    cols.push(cur);
    return cols;
  }

  function computeRingBboxAndCentroid (arg0_ring) {
    let ring = arg0_ring;
    let min_lng = Infinity, min_lat = Infinity, max_lng = -Infinity, max_lat = -Infinity;
    let area2 = 0, cx = 0, cy = 0;
    for (let i = 0; i < ring.length; i++) {
      let x = ring[i][0];
      let y = ring[i][1];
      if (x < min_lng) min_lng = x;
      if (x > max_lng) max_lng = x;
      if (y < min_lat) min_lat = y;
      if (y > max_lat) max_lat = y;
      let j = (i + 1)%ring.length;
      let cross = x*ring[j][1] - ring[j][0]*y;
      area2 += cross;
      cx += (x + ring[j][0])*cross;
      cy += (y + ring[j][1])*cross;
    }
    let area = Math.abs(area2)/2;
    let centroid = (Math.abs(area2) > 1e-12) ?
      [cy/(3*area2), cx/(3*area2)] :
      [(min_lat + max_lat)/2, (min_lng + max_lng)/2];
    return { area: area, bbox: [min_lng, min_lat, max_lng, max_lat], centroid: centroid };
  }

  function indexGeoJSONFeature (arg0_feature) {
    let feat = arg0_feature;
    let geom = feat.geometry;
    if (!geom || !geom.coordinates) return null;
    let polys = (geom.type === "Polygon") ? [geom.coordinates] :
      ((geom.type === "MultiPolygon") ? geom.coordinates : []);
    let poly_meta = [];
    let f_min_lng = Infinity, f_min_lat = Infinity, f_max_lng = -Infinity, f_max_lat = -Infinity;
    let total_area = 0, w_lat = 0, w_lng = 0;

    for (let i = 0; i < polys.length; i++) {
      let outer = polys[i][0];
      if (!outer || outer.length < 3) continue;
      let meta = computeRingBboxAndCentroid(outer);
      poly_meta.push({ rings: polys[i], bbox: meta.bbox, area: meta.area, centroid: meta.centroid });
      if (meta.bbox[0] < f_min_lng) f_min_lng = meta.bbox[0];
      if (meta.bbox[1] < f_min_lat) f_min_lat = meta.bbox[1];
      if (meta.bbox[2] > f_max_lng) f_max_lng = meta.bbox[2];
      if (meta.bbox[3] > f_max_lat) f_max_lat = meta.bbox[3];
      total_area += meta.area;
      w_lat += meta.centroid[0]*meta.area;
      w_lng += meta.centroid[1]*meta.area;
    }

    let area_centroid = (total_area > 0) ? [w_lat/total_area, w_lng/total_area] :
      [(f_min_lat + f_max_lat)/2, (f_min_lng + f_max_lng)/2];
    let bbox_center = [(f_min_lat + f_max_lat)/2, (f_min_lng + f_max_lng)/2];

    return {
      properties: feat.properties || {},
      geometry: geom,
      polys: poly_meta,
      bbox: [f_min_lng, f_min_lat, f_max_lng, f_max_lat],
      area_centroid: area_centroid,
      bbox_center: bbox_center
    };
  }

  /**
   * Ray-casting point-in-ring test for [lng, lat].
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Array<Array<number>>} arg2_ring
   * @returns {boolean}
   */
  function pointInRing (arg0_lng, arg1_lat, arg2_ring) {
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let ring = arg2_ring;
    if (!ring || ring.length < 3) return false;
    let inside = false;
    for (let i = 0, x = ring.length - 1; i < ring.length; x = i++) {
      let xi = ring[i][0], yi = ring[i][1];
      let xj = ring[x][0], yj = ring[x][1];
      let intersect = ((yi > lat) !== (yj > lat)) &&
        (lng < (xj - xi)*(lat - yi)/((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  /**
   * Checks whether [lat, lng] falls inside an indexed feature or raw GeoJSON geometry.
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {Object} arg2_indexed_or_geom
   * @returns {boolean}
   */
  function pointInGeometry (arg0_lat, arg1_lng, arg2_indexed_or_geom) {
    let lat = Number(arg0_lat);
    let lng = normLng(arg1_lng);
    let target = arg2_indexed_or_geom;
    if (!target || !Number.isFinite(lat) || !Number.isFinite(lng)) return false;

    if (target.polys) {
      let b = target.bbox;
      if (lat < b[1] || lat > b[3] || lng < b[0] || lng > b[2]) return false;
      for (let i = 0; i < target.polys.length; i++) {
        let pm = target.polys[i];
        let pb = pm.bbox;
        if (lat < pb[1] || lat > pb[3] || lng < pb[0] || lng > pb[2]) continue;
        if (!pointInRing(lng, lat, pm.rings[0])) continue;
        let in_hole = false;
        for (let h = 1; h < pm.rings.length; h++) {
          if (pointInRing(lng, lat, pm.rings[h])) { in_hole = true; break; }
        }
        if (!in_hole) return true;
      }
      return false;
    }

    let geom = target.geometry ? target.geometry : target;
    let polys = (geom.type === "Polygon") ? [geom.coordinates] :
      ((geom.type === "MultiPolygon") ? geom.coordinates : []);
    for (let i = 0; i < polys.length; i++) {
      let rings = polys[i];
      if (!rings[0] || !pointInRing(lng, lat, rings[0])) continue;
      let in_hole = false;
      for (let h = 1; h < rings.length; h++) {
        if (pointInRing(lng, lat, rings[h])) { in_hole = true; break; }
      }
      if (!in_hole) return true;
    }
    return false;
  }

  function pointToSegmentDistKm (arg0_lat, arg1_lng, arg2_p1, arg3_p2) {
    let lat = arg0_lat;
    let lng = arg1_lng;
    let x1 = arg2_p1[0], y1 = arg2_p1[1];
    let x2 = arg3_p2[0], y2 = arg3_p2[1];
    let cos_lat = Math.cos(lat*Math.PI/180);
    let dx = (x2 - x1)*cos_lat;
    let dy = (y2 - y1);
    let len2 = dx*dx + dy*dy;
    let t = (len2 > 1e-14) ?
      Math.max(0, Math.min(1, ((lng - x1)*cos_lat*dx + (lat - y1)*dy)/len2)) : 0;
    let proj_lng = x1 + t*(x2 - x1);
    let proj_lat = y1 + t*(y2 - y1);
    return haversineDistanceKm([lat, lng], [proj_lat, proj_lng]);
  }

  /**
   * Computes minimum distance in km from [lat, lng] to an indexed feature (0 if inside).
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {Object} arg2_indexed_feat
   * @param {number} [arg3_max_search_km=Infinity]
   * @returns {number}
   */
  function distanceToGeometryKm (arg0_lat, arg1_lng, arg2_indexed_feat, arg3_max_search_km) {
    let lat = Number(arg0_lat);
    let lng = normLng(arg1_lng);
    let feat = arg2_indexed_feat;
    let max_km = (arg3_max_search_km !== undefined) ? arg3_max_search_km : Infinity;
    if (!feat || !feat.polys) return Infinity;
    if (pointInGeometry(lat, lng, feat)) return 0;

    let min_dist = Infinity;
    let cos_lat = Math.max(0.05, Math.cos(lat*Math.PI/180));
    let deg_pad_lat = (Number.isFinite(max_km)) ? max_km/111.0 + 0.5 : Infinity;
    let deg_pad_lng = (Number.isFinite(max_km)) ? max_km/(111.0*cos_lat) + 0.5 : Infinity;

    for (let i = 0; i < feat.polys.length; i++) {
      let pm = feat.polys[i];
      let pb = pm.bbox;
      if (Number.isFinite(max_km)) {
        if (lat < pb[1] - deg_pad_lat || lat > pb[3] + deg_pad_lat) continue;
        let d_lng_box = 0;
        if (lng < pb[0]) d_lng_box = pb[0] - lng;
        else if (lng > pb[2]) d_lng_box = lng - pb[2];
        if (d_lng_box > 180) d_lng_box = 360 - d_lng_box;
        if (d_lng_box > deg_pad_lng) continue;
      }
      let ring = pm.rings[0];
      for (let k = 0; k < ring.length - 1; k++) {
        let d = pointToSegmentDistKm(lat, lng, ring[k], ring[k + 1]);
        if (d < min_dist) min_dist = d;
      }
    }
    return min_dist;
  }

  /**
   * Checks whether [lat, lng] falls inside a bounding box (handling +/-180 antimeridian wrap).
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {Object} arg2_box
   * @param {number} [arg3_pad_deg=0]
   * @returns {boolean}
   */
  function pointInBox (arg0_lat, arg1_lng, arg2_box, arg3_pad_deg) {
    let lat = Number(arg0_lat);
    let lng = normLng(arg1_lng);
    let box = arg2_box;
    let pad = arg3_pad_deg || 0;
    if (!box || !Number.isFinite(lat) || !Number.isFinite(lng)) return false;
    if (lat < box.min_lat - pad || lat > box.max_lat + pad) return false;
    if (box.wrap_pos_lng_min !== undefined && lng >= box.wrap_pos_lng_min - pad) return true;
    let min_x = normLng(box.min_lng - pad);
    let max_x = normLng(box.max_lng + pad);
    if (box.min_lng <= box.max_lng && min_x <= max_x)
      return lng >= min_x && lng <= max_x;
    return lng >= min_x || lng <= max_x;
  }

  /**
   * Computes approximate distance in km from [lat, lng] to a bounding box (0 if inside).
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {Object} arg2_box
   * @returns {number}
   */
  function distanceToBoxKm (arg0_lat, arg1_lng, arg2_box) {
    let lat = Number(arg0_lat);
    let lng = normLng(arg1_lng);
    let box = arg2_box;
    if (!box) return Infinity;
    if (pointInBox(lat, lng, box, 0)) return 0;

    let clamp_lat = Math.max(box.min_lat, Math.min(box.max_lat, lat));
    let clamp_lng = lng;
    if (box.min_lng <= box.max_lng) {
      let d_min = Math.abs(normLng(lng - box.min_lng));
      let d_max = Math.abs(normLng(lng - box.max_lng));
      if (lng < box.min_lng || lng > box.max_lng)
        clamp_lng = (d_min <= d_max) ? box.min_lng : box.max_lng;
    } else {
      let d_min = Math.abs(normLng(lng - box.min_lng));
      let d_max = Math.abs(normLng(lng - box.max_lng));
      clamp_lng = (d_min <= d_max) ? box.min_lng : box.max_lng;
    }
    return haversineDistanceKm([lat, lng], [clamp_lat, clamp_lng]);
  }

  /**
   * Reads a 4320x2160 Float32 GeoPNG raster into { width, height, data: Float32Array }.
   * @param {string} arg0_path
   * @returns {{width: number, height: number, data: Float32Array}|null}
   */
  function readFloat32Raster (arg0_path) {
    if (!arg0_path || !fs.existsSync(arg0_path)) return null;
    let png_obj = pngjs.PNG.sync.read(fs.readFileSync(arg0_path));
    let dv = new DataView(png_obj.data.buffer, png_obj.data.byteOffset, png_obj.data.byteLength);
    let total = png_obj.width*png_obj.height;
    let out = new Float32Array(total);
    for (let i = 0; i < total; i++) {
      let v = dv.getFloat32(i*4, false);
      out[i] = (Number.isFinite(v) && v > 0) ? v : 0;
    }
    return { width: png_obj.width, height: png_obj.height, data: out };
  }

  /**
   * Reads a 4320x2160 Uint32 GeoPNG raster (e.g. HYDE land_area.png) into { width, height, data: Uint32Array }.
   * @param {string} arg0_path
   * @returns {{width: number, height: number, data: Uint32Array}|null}
   */
  function readUint32Raster (arg0_path) {
    if (!arg0_path || !fs.existsSync(arg0_path)) return null;
    let png_obj = pngjs.PNG.sync.read(fs.readFileSync(arg0_path));
    let dv = new DataView(png_obj.data.buffer, png_obj.data.byteOffset, png_obj.data.byteLength);
    let total = png_obj.width*png_obj.height;
    let out = new Uint32Array(total);
    for (let i = 0; i < total; i++) out[i] = dv.getUint32(i*4, false);
    return { width: png_obj.width, height: png_obj.height, data: out };
  }

  /**
   * Converts [lat, lng] to [px, py] pixel coordinates on a 4320x2160 equirectangular GeoPNG.
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {Object} [arg2_options]
   * @returns {Array<number>}
   */
  function coordsToPixel (arg0_lat, arg1_lng, arg2_options) {
    let options = arg2_options || {};
    let width = options.width || 4320;
    let height = options.height || 2160;
    let dy = options.dy || 0;
    let lat = Math.max(-90, Math.min(90, Number(arg0_lat)));
    let lng = normLng(arg1_lng);
    let px = Math.min(width - 1, Math.max(0, Math.floor(((lng + 180)/360)*width)));
    let py = Math.min(height - 1, Math.max(0, Math.floor(((90 - lat)/180)*height) + dy));
    return [px, py];
  }

  /**
   * Samples center value, 3x3 sum, and 3x3 max around [lat, lng] from a loaded raster.
   * @param {Object} arg0_raster
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @param {number} [arg3_dy=0]
   * @returns {{center: number, sum3x3: number, max3x3: number, px: number, py: number}}
   */
  function sampleRaster3x3 (arg0_raster, arg1_lat, arg2_lng, arg3_dy) {
    let raster = arg0_raster;
    if (!raster || !raster.data) return { center: 0, sum3x3: 0, max3x3: 0, px: 0, py: 0 };
    let [cx, cy] = coordsToPixel(arg1_lat, arg2_lng, { width: raster.width, height: raster.height, dy: arg3_dy || 0 });
    let sum = 0, max_v = 0, center = 0;
    for (let oy = -1; oy <= 1; oy++) {
      let py = Math.min(raster.height - 1, Math.max(0, cy + oy));
      for (let ox = -1; ox <= 1; ox++) {
        let px = ((cx + ox)%raster.width + raster.width)%raster.width;
        let v = raster.data[py*raster.width + px] || 0;
        sum += v;
        if (v > max_v) max_v = v;
        if (ox === 0 && oy === 0) center = v;
      }
    }
    return { center: center, sum3x3: sum, max3x3: max_v, px: cx, py: cy };
  }

  /**
   * Samples GHS_POP_2000 (dy=-1), GHS_POP_2020 (dy=0), GHS_POP_2025 (dy=0), and HYDE land_area (dy=0).
   * @param {Object} arg0_ctx
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @returns {Object}
   */
  function sampleGHSPop (arg0_ctx, arg1_lat, arg2_lng) {
    let ctx = arg0_ctx;
    let p2000 = sampleRaster3x3(ctx.rasters.ghs_pop_2000, arg1_lat, arg2_lng, -1);
    let p2020 = sampleRaster3x3(ctx.rasters.ghs_pop_2020, arg1_lat, arg2_lng, 0);
    let p2025 = sampleRaster3x3(ctx.rasters.ghs_pop_2025, arg1_lat, arg2_lng, 0);
    let land = sampleRaster3x3(ctx.rasters.land_area, arg1_lat, arg2_lng, 0);
    return {
      ghs2000_center: p2000.center,
      ghs2000_3x3: p2000.sum3x3,
      ghs2020_center: p2020.center,
      ghs2020_3x3: p2020.sum3x3,
      ghs2025_center: p2025.center,
      ghs2025_3x3: p2025.sum3x3,
      ghs_max_3x3: Math.max(p2000.sum3x3, p2020.sum3x3, p2025.sum3x3),
      land_center: land.center,
      land_3x3: land.sum3x3
    };
  }

  /**
   * Lazily samples iso2.png at [lat, lng] returning { iso2, country, rgb }.
   * @param {Object} arg0_ctx
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @returns {{iso2: string|null, country: string|null, rgb: string}}
   */
  function sampleIso2 (arg0_ctx, arg1_lat, arg2_lng) {
    let ctx = arg0_ctx;
    if (!ctx._iso2_cache) {
      let png_obj = pngjs.PNG.sync.read(fs.readFileSync(PATHS.iso2_png));
      let lines = fs.readFileSync(PATHS.iso2_geocodes, "utf8").split(/\r?\n/).filter(Boolean);
      let map = new Map();
      for (let i = 1; i < lines.length; i++) {
        let parts = lines[i].split(";");
        if (parts.length >= 4) map.set(parts[3].trim(), { iso2: parts[0].trim(), country: parts[2].trim() });
      }
      ctx._iso2_cache = { png: png_obj, map: map };
    }
    let cache = ctx._iso2_cache;
    let [px, py] = coordsToPixel(arg1_lat, arg2_lng, { width: cache.png.width, height: cache.png.height, dy: 0 });
    let idx = (py*cache.png.width + px)*4;
    let rgb = `${cache.png.data[idx]},${cache.png.data[idx + 1]},${cache.png.data[idx + 2]}`;
    let hit = cache.map.get(rgb);
    return { iso2: hit ? hit.iso2 : null, country: hit ? hit.country : null, rgb: rgb };
  }

  function loadUCDBDatabase (arg0_options) {
    let options = arg0_options || {};
    let csv_path = options.ucdb_csv || PATHS.ucdb_csv;
    let markers_path = options.ucdb_markers || PATHS.ucdb_markers;
    let ghsl_path = options.ghsl_json || PATHS.ghsl_json;

    let coords_by_id = new Map();
    if (fs.existsSync(markers_path)) {
      let markers = JSON.parse(fs.readFileSync(markers_path, "utf8"));
      for (let i = 0; i < markers.features.length; i++) {
        let f = markers.features[i];
        let id = Number(f.properties && f.properties.ID_MTUC_G0);
        if (Number.isFinite(id) && f.geometry && Array.isArray(f.geometry.coordinates))
          coords_by_id.set(id, [Number(f.geometry.coordinates[1]), Number(f.geometry.coordinates[0])]);
      }
    } else if (fs.existsSync(ghsl_path)) {
      let ghsl_obj = JSON.parse(fs.readFileSync(ghsl_path, "utf8"));
      for (let k of Object.keys(ghsl_obj)) {
        let g = ghsl_obj[k];
        if (g && g.id && Array.isArray(g.coords)) coords_by_id.set(Number(g.id), g.coords);
      }
    }

    let raw_text = fs.readFileSync(csv_path, "utf8").replace(/^\uFEFF/, "");
    let lines = raw_text.split(/\r?\n/);
    let headers = parseSemicolonCSVLine(lines[0]).map(s => s.trim());
    let id_idx = headers.indexOf("ID_MTUC_G0");
    let main_idx = headers.indexOf("GC_UCN_MAI_2025");
    let list_idx = headers.indexOf("GC_UCN_LIS_2025");
    let cnt_idx = headers.indexOf("GC_CNT_GAD_2025");
    let p2000_idx = headers.indexOf("MT_POP_TOT_2000");
    let p2025_idx = headers.indexOf("MT_POP_TOT_2025");

    let entries = [];
    let by_id = new Map();
    let by_name = new Map();
    let spatial_grid = new Map();

    function parseEuroInt (s) {
      if (!s) return 0;
      let cleaned = String(s).trim().replace(/\./g, "").replace(",", ".");
      let v = parseFloat(cleaned);
      return (Number.isFinite(v) && v > 0) ? Math.round(v) : 0;
    }

    for (let i = 1; i < lines.length; i++) {
      let line = lines[i].trim();
      if (!line) continue;
      let cols = parseSemicolonCSVLine(line);
      let id = Number(cols[id_idx]);
      if (!Number.isFinite(id) || id <= 0) continue;
      let coords = coords_by_id.get(id);
      if (!coords) continue;

      let main_name = String(cols[main_idx] || "").trim();
      let list_raw = String(cols[list_idx] || "").trim();
      let country = (cols[cnt_idx] && cols[cnt_idx] !== "#N/A") ? String(cols[cnt_idx]).trim() : "";
      let pop2000 = parseEuroInt(cols[p2000_idx]);
      let pop2025 = parseEuroInt(cols[p2025_idx]);
      let list_tokens = list_raw ? list_raw.split(";").map(s => s.trim()).filter(Boolean) : [];
      let norm_names = new Set();
      let main_norm = normaliseName(main_name);
      if (main_norm) norm_names.add(main_norm);
      for (let t = 0; t < list_tokens.length; t++) {
        let tn = normaliseName(list_tokens[t]);
        if (tn) norm_names.add(tn);
      }

      let rec = {
        id: id,
        name: main_name,
        list_names: list_tokens,
        country: country,
        coords: coords,
        pop2000: pop2000,
        pop2025: pop2025,
        pop_ref: Math.max(pop2000, pop2025),
        norm_names: Array.from(norm_names)
      };
      entries.push(rec);
      by_id.set(id, rec);

      for (let n of rec.norm_names) {
        if (!by_name.has(n)) by_name.set(n, []);
        by_name.get(n).push(rec);
      }
      let gk = `${Math.floor(coords[0])},${Math.floor(coords[1])}`;
      if (!spatial_grid.has(gk)) spatial_grid.set(gk, []);
      spatial_grid.get(gk).push(rec);
    }

    return { entries: entries, by_id: by_id, by_name: by_name, spatial_grid: spatial_grid };
  }

  /**
   * Loads and caches all GeoJSONs, CShapes, GeoPNG rasters, and UCDB tables into a reusable audit context.
   * @param {Object} [arg0_options]
   * @returns {Object}
   */
  function loadAuditContext (arg0_options) {
    let options = arg0_options || {};
    if (_cached_context && !options.force_reload) return _cached_context;

    let populstat_countries = JSON5.parse(fs.readFileSync(options.populstat_countries || PATHS.populstat_countries, "utf8"));
    let ne_raw = JSON.parse(fs.readFileSync(options.ne_countries || PATHS.ne_countries, "utf8"));
    let ne_by_admin = new Map();
    let ne_features = [];
    for (let i = 0; i < ne_raw.features.length; i++) {
      let indexed = indexGeoJSONFeature(ne_raw.features[i]);
      if (!indexed) continue;
      ne_features.push(indexed);
      let adm = indexed.properties.ADMIN;
      if (!ne_by_admin.has(adm)) ne_by_admin.set(adm, []);
      ne_by_admin.get(adm).push(indexed);
    }

    let cshapes_raw = JSON.parse(fs.readFileSync(options.cshapes || PATHS.cshapes, "utf8"));
    let cshapes_1991_by_name = new Map();
    for (let i = 0; i < cshapes_raw.features.length; i++) {
      let f = cshapes_raw.features[i];
      let p = f.properties || {};
      if (p.gwsyear <= 1995 && p.gweyear >= 1991) {
        let indexed = indexGeoJSONFeature(f);
        if (indexed && !cshapes_1991_by_name.has(p.cntry_name))
          cshapes_1991_by_name.set(p.cntry_name, indexed);
      }
    }

    let rasters = {
      ghs_pop_2000: readFloat32Raster(options.ghs_pop_2000 || PATHS.ghs_pop_2000),
      ghs_pop_2020: readFloat32Raster(options.ghs_pop_2020 || PATHS.ghs_pop_2020),
      ghs_pop_2025: readFloat32Raster(options.ghs_pop_2025 || PATHS.ghs_pop_2025),
      land_area: readUint32Raster(options.land_area || PATHS.land_area)
    };

    let ucdb = loadUCDBDatabase(options);

    _cached_context = {
      cshapes_1991_by_name: cshapes_1991_by_name,
      ne_by_admin: ne_by_admin,
      ne_features: ne_features,
      populstat_countries: populstat_countries,
      rasters: rasters,
      ucdb: ucdb
    };
    return _cached_context;
  }

  /**
   * Resolves a raw country key or name to a canonical country name.
   * @param {Object} arg0_ctx
   * @param {string} arg1_country_or_key
   * @returns {string}
   */
  function resolveCanonicalCountry (arg0_ctx, arg1_country_or_key) {
    let ctx = arg0_ctx;
    let raw = String(arg1_country_or_key || "").trim();
    if (!raw) return "";
    if (ctx && ctx.populstat_countries && ctx.populstat_countries[raw])
      raw = ctx.populstat_countries[raw];
    let lower = raw.toLowerCase();
    if (COUNTRY_ALIASES[lower]) return COUNTRY_ALIASES[lower];
    return raw;
  }

  /**
   * Checks whether two country names/keys refer to compatible jurisdictions (including US states, China/HK/Macau, Serbia/Kosovo/Montenegro, Cyprus/N.Cyprus, Morocco/W.Sahara, Israel/Palestine).
   * @param {Object} arg0_ctx
   * @param {string} arg1_country_a
   * @param {string} arg2_country_b
   * @returns {boolean}
   */
  function areCompatibleCountries (arg0_ctx, arg1_country_a, arg2_country_b) {
    let a = resolveCanonicalCountry(arg0_ctx, arg1_country_a);
    let b = resolveCanonicalCountry(arg0_ctx, arg2_country_b);
    if (!a || !b) return false;
    if (a.toLowerCase() === b.toLowerCase()) return true;

    let us_names = new Set(Object.values(US_STATE_BOUNDS).map(s => s.name));
    us_names.add("United States");
    if (us_names.has(a) && us_names.has(b)) return true;

    let groups = [
      new Set(["China", "Hong Kong", "Macau"]),
      new Set(["Serbia", "Kosovo", "Montenegro"]),
      new Set(["Cyprus", "Northern Cyprus"]),
      new Set(["Morocco", "Western Sahara"]),
      new Set(["Israel", "Palestine"]),
      new Set(["Congo", "Republic of the Congo", "Democratic Republic of the Congo"]),
      new Set(["Korea", "South Korea", "North Korea"]),
      new Set(["United Kingdom", "Jersey", "Guernsey", "Isle of Man"]),
      new Set(["France", "Réunion", "Guadeloupe", "Martinique", "French Guiana", "Mayotte"])
    ];
    for (let i = 0; i < groups.length; i++)
      if (groups[i].has(a) && groups[i].has(b)) return true;
    return false;
  }

  function getCountryRule (arg0_ctx, arg1_raw_key_or_name) {
    let raw = String(arg1_raw_key_or_name || "").trim();
    let canonical = resolveCanonicalCountry(arg0_ctx, raw);
    let us_names = new Set(Object.values(US_STATE_BOUNDS).map(s => s.name));
    if (raw.toLowerCase().startsWith("usas-") || (us_names.has(canonical) && raw.toLowerCase() !== "georgia" && canonical !== "Georgia"))
      canonical = "United States";

    let rule = TERRITORY_RULES[canonical];
    if (rule) return { canonical: canonical, rule: rule };
    return { canonical: canonical, rule: { primary: [canonical] } };
  }

  /**
   * Checks whether [lat, lng] lies inside or within 20km of target country/territory polygons or archipelago boxes.
   * @param {Object} arg0_ctx
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @param {string} arg3_country_or_key
   * @returns {Object}
   */
  function checkCountryMembership (arg0_ctx, arg1_lat, arg2_lng, arg3_country_or_key) {
    let ctx = arg0_ctx;
    let lat = Number(arg1_lat);
    let lng = normLng(arg2_lng);
    let raw = String(arg3_country_or_key || "").trim();
    let { canonical, rule } = getCountryRule(ctx, raw);
    let max_border_km = 20.0;

    let actual_at_pt = [];
    for (let i = 0; i < ctx.ne_features.length; i++) {
      let nf = ctx.ne_features[i];
      if (pointInGeometry(lat, lng, nf)) actual_at_pt.push(nf.properties.ADMIN);
    }

    // Check CShapes 1991 borders (e.g. Ukraine Crimea)
    if (rule.cshapes_1991) {
      let cs_feat = ctx.cshapes_1991_by_name.get(rule.cshapes_1991);
      if (cs_feat && pointInGeometry(lat, lng, cs_feat)) {
        return {
          valid: true, inside_polygon: true, inside_archipelago: false, inside_dependency: false,
          dependency_mismatch: false, dist_km: 0, matched_admin: rule.cshapes_1991 + " (1991)",
          expected_canonical: canonical, actual_countries_at_point: actual_at_pt
        };
      }
    }

    // Check archipelago / small-island bounding boxes (handles +/-180 wrap and tiny missing atolls in NE 50m)
    let arch_boxes = ARCHIPELAGO_BOUNDS[canonical];
    if (arch_boxes) {
      let allowed_admins = new Set(rule.primary || []);
      let hits_foreign = actual_at_pt.some(adm => !allowed_admins.has(adm));
      if (!hits_foreign) {
        for (let i = 0; i < arch_boxes.length; i++) {
          if (pointInBox(lat, lng, arch_boxes[i], 0.15)) {
            return {
              valid: true, inside_polygon: actual_at_pt.some(a => allowed_admins.has(a)),
              inside_archipelago: true, inside_dependency: false, dependency_mismatch: false,
              dist_km: 0, matched_admin: arch_boxes[i].name || canonical,
              expected_canonical: canonical, actual_countries_at_point: actual_at_pt
            };
          }
        }
      }
    }

    // Check explicit extra boxes (e.g. Spain Canaries/Ceuta, Portugal Azores/Madeira, UK Gibraltar, island territories)
    if (rule.allow_boxes) {
      let allowed_admins = new Set(rule.primary || []);
      let hits_foreign = actual_at_pt.some(adm => !allowed_admins.has(adm));
      for (let i = 0; i < rule.allow_boxes.length; i++) {
        let ab = rule.allow_boxes[i];
        if ((!hits_foreign || ab.ignore_foreign) && pointInBox(lat, lng, ab, 0.15)) {
          return {
            valid: true, inside_polygon: true, inside_archipelago: !ab.ignore_foreign, inside_dependency: false,
            dependency_mismatch: false, dist_km: 0, matched_admin: ab.name || canonical,
            expected_canonical: canonical, actual_countries_at_point: actual_at_pt
          };
        }
      }
    }

    // Check primary NE polygons (respecting metro_box when separating e.g. France metro vs French Guiana)
    let min_primary_dist = Infinity;
    let matched_primary = null;
    for (let i = 0; i < (rule.primary || []).length; i++) {
      let adm = rule.primary[i];
      let feats = ctx.ne_by_admin.get(adm) || [];
      for (let x = 0; x < feats.length; x++) {
        let d = distanceToGeometryKm(lat, lng, feats[x], 500);
        if (d < min_primary_dist) { min_primary_dist = d; matched_primary = adm; }
      }
    }

    if (min_primary_dist <= max_border_km) {
      let dep_mismatch = false;
      if (rule.metro_box) {
        let in_metro = pointInBox(lat, lng, rule.metro_box, 0.2);
        let in_allow = (rule.allow_boxes || []).some(b => pointInBox(lat, lng, b, 0.15));
        if (!in_metro && !in_allow) dep_mismatch = true;
      }
      return {
        valid: !dep_mismatch || (raw === "france" || raw === "netherl" || raw === "denmark" || raw === "norway" || raw === "unkingd" || raw === "usa" || raw === "spain" || raw === "portuga"),
        inside_polygon: min_primary_dist === 0,
        inside_archipelago: false,
        inside_dependency: dep_mismatch,
        dependency_mismatch: dep_mismatch,
        dist_km: Math.round(min_primary_dist*10)/10,
        matched_admin: matched_primary,
        expected_canonical: canonical,
        actual_countries_at_point: actual_at_pt
      };
    }

    // Check dependency polygons for metropolitan keys
    let min_dep_dist = Infinity;
    let matched_dep = null;
    for (let i = 0; i < (rule.dependencies || []).length; i++) {
      let adm = rule.dependencies[i];
      let feats = ctx.ne_by_admin.get(adm) || [];
      for (let x = 0; x < feats.length; x++) {
        let d = distanceToGeometryKm(lat, lng, feats[x], 500);
        if (d < min_dep_dist) { min_dep_dist = d; matched_dep = adm; }
      }
    }
    if (min_dep_dist <= max_border_km) {
      return {
        valid: true, inside_polygon: min_dep_dist === 0, inside_archipelago: false,
        inside_dependency: true, dependency_mismatch: true,
        dist_km: Math.round(min_dep_dist*10)/10, matched_admin: matched_dep,
        expected_canonical: canonical, actual_countries_at_point: actual_at_pt
      };
    }

    // Compute full global distance for primary features if beyond 500km
    if (!Number.isFinite(min_primary_dist)) {
      for (let i = 0; i < (rule.primary || []).length; i++) {
        let feats = ctx.ne_by_admin.get(rule.primary[i]) || [];
        for (let x = 0; x < feats.length; x++) {
          let d = distanceToGeometryKm(lat, lng, feats[x], Infinity);
          if (d < min_primary_dist) { min_primary_dist = d; matched_primary = rule.primary[i]; }
        }
      }
    }

    return {
      valid: false, inside_polygon: false, inside_archipelago: false, inside_dependency: false,
      dependency_mismatch: false, dist_km: Math.round(min_primary_dist*10)/10,
      matched_admin: matched_primary, expected_canonical: canonical,
      actual_countries_at_point: actual_at_pt
    };
  }

  /**
   * Validates coordinates against a US state's bounding box and state centroid (for usas-* keys or state hints).
   * @param {number} arg0_lat
   * @param {number} arg1_lng
   * @param {string} arg2_state_key_or_code
   * @returns {Object}
   */
  function checkUSState (arg0_lat, arg1_lng, arg2_state_key_or_code) {
    let lat = Number(arg0_lat);
    let lng = normLng(arg1_lng);
    let raw = String(arg2_state_key_or_code || "").trim();
    let code = raw.toLowerCase().startsWith("usas-") ? raw.slice(5).toUpperCase() : raw.toUpperCase();
    let box = US_STATE_BOUNDS[code];
    if (!box) {
      let by_name = Object.entries(US_STATE_BOUNDS).find(([, v]) => v.name.toLowerCase() === raw.toLowerCase());
      if (by_name) { code = by_name[0]; box = by_name[1]; }
    }
    if (!box) return { valid: true, state_code: null, state_name: raw, inside_bbox: false, dist_to_bbox_km: 0, dist_to_centroid_km: Infinity, at_state_centroid: false };

    let inside_bbox = pointInBox(lat, lng, box, 0.05);
    let dist_bbox = inside_bbox ? 0 : distanceToBoxKm(lat, lng, box);
    let dist_centroid = haversineDistanceKm([lat, lng], box.centroid);
    return {
      valid: dist_bbox <= 15.0,
      state_code: code,
      state_name: box.name,
      inside_bbox: inside_bbox,
      dist_to_bbox_km: Math.round(dist_bbox*10)/10,
      dist_to_centroid_km: Math.round(dist_centroid*10)/10,
      at_state_centroid: dist_centroid <= 10.0
    };
  }

  /**
   * Checks whether [lat, lng] lies within 10km of the target country's NE centroid, bbox center, or Google fallback centroid.
   * @param {Object} arg0_ctx
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @param {string} arg3_country_or_key
   * @returns {{near_centroid: boolean, min_dist_km: number, centroid_type: string|null, centroid_coords: Array<number>|null}}
   */
  function checkCountryCentroidProximity (arg0_ctx, arg1_lat, arg2_lng, arg3_country_or_key) {
    let ctx = arg0_ctx;
    let { canonical, rule } = getCountryRule(ctx, arg3_country_or_key);
    let candidates = [];
    if (GOOGLE_CENTROIDS[canonical])
      candidates.push({ type: "google", coords: GOOGLE_CENTROIDS[canonical] });
    for (let i = 0; i < (rule.primary || []).length; i++) {
      let feats = ctx.ne_by_admin.get(rule.primary[i]) || [];
      for (let x = 0; x < feats.length; x++) {
        candidates.push({ type: "ne_area", coords: feats[x].area_centroid });
        candidates.push({ type: "ne_bbox", coords: feats[x].bbox_center });
      }
    }
    let best_dist = Infinity, best_type = null, best_coords = null;
    for (let i = 0; i < candidates.length; i++) {
      let d = haversineDistanceKm([arg1_lat, arg2_lng], candidates[i].coords);
      if (d < best_dist) {
        best_dist = d;
        best_type = candidates[i].type;
        best_coords = candidates[i].coords;
      }
    }
    return {
      near_centroid: best_dist <= 10.0,
      min_dist_km: Math.round(best_dist*10)/10,
      centroid_type: best_type,
      centroid_coords: best_coords
    };
  }

  /**
   * Extracts subnational hint { field, value } from a Populstat or historical entry.
   * @param {Object} arg0_entry
   * @returns {{field: string, value: string}|null}
   */
  function extractSubnationalHint (arg0_entry) {
    let entry = arg0_entry;
    if (!entry || typeof entry !== "object") return null;
    for (let i = 0; i < SUBNATIONAL_FIELDS.length; i++) {
      let f = SUBNATIONAL_FIELDS[i];
      if (entry[f] !== undefined && entry[f] !== null && String(entry[f]).trim() !== "")
        return { field: f, value: String(entry[f]).trim() };
    }
    return null;
  }

  /**
   * Parses Populstat integer `position` field (DDMMDDDMM) into [lat, lng] using refCoords for hemisphere signs.
   * @param {number|string} arg0_pos
   * @param {Array<number>} [arg1_ref_coords]
   * @returns {Array<number>|null}
   */
  function parsePopulstatPosition (arg0_pos, arg1_ref_coords) {
    let s = String(arg0_pos || "").trim();
    if (!/^\d{8,9}$/.test(s)) return null;
    let lat_deg = parseInt(s.slice(0, 2), 10);
    let lat_min = parseInt(s.slice(2, 4), 10);
    let lng_part = s.slice(4);
    let lng_deg = parseInt(lng_part.slice(0, lng_part.length - 2), 10);
    let lng_min = parseInt(lng_part.slice(-2), 10);
    if (lat_deg > 90 || lat_min >= 60 || lng_deg > 180 || lng_min >= 60) return null;
    let lat = lat_deg + lat_min/60;
    let lng = lng_deg + lng_min/60;
    if (Array.isArray(arg1_ref_coords) && arg1_ref_coords.length >= 2) {
      if (arg1_ref_coords[0] < 0) lat = -lat;
      if (arg1_ref_coords[1] < 0) lng = -lng;
    }
    return [lat, lng];
  }

  /**
   * Extracts all normalised names for a settlement entry.
   * @param {Object} arg0_entry
   * @returns {Array<string>}
   */
  function extractAllNames (arg0_entry) {
    let e = arg0_entry;
    if (!e) return [];
    let set = new Set();
    let add = (s) => { let n = normaliseName(s); if (n) set.add(n); };
    add(e.name);
    if (Array.isArray(e.other_names)) e.other_names.forEach(add);
    if (Array.isArray(e.original_names)) e.original_names.forEach(add);
    if (typeof e["variants of the name"] === "string") e["variants of the name"].split(/[;,]/).forEach(add);
    return Array.from(set);
  }

  /**
   * Checks whether two co-located entries are legitimate variants/agglomerations of the same settlement.
   * @param {Object} arg0_entry_a
   * @param {Object} arg1_entry_b
   * @returns {boolean}
   */
  function isAgglomerationOrVariantPair (arg0_entry_a, arg1_entry_b) {
    let names_a = extractAllNames(arg0_entry_a);
    let names_b = extractAllNames(arg1_entry_b);
    for (let i = 0; i < names_a.length; i++) {
      for (let x = 0; x < names_b.length; x++) {
        if (names_a[i] === names_b[x]) return true;
        if (names_b[x].startsWith(names_a[i] + " ") && /\b(county|balance|central|inner|outer|municip|metro)\b/.test(names_b[x])) return true;
        if (names_a[i].startsWith(names_b[x] + " ") && /\b(county|balance|central|inner|outer|municip|metro)\b/.test(names_a[i])) return true;
      }
    }

    let part_a = String(arg0_entry_a.particulars || "").toLowerCase();
    let part_b = String(arg1_entry_b.particulars || "").toLowerCase();
    let checkAgg = (part, other_names) => {
      let m = part.match(/agglomeration of\s+(.+)/);
      if (!m) return false;
      let target = normaliseName(m[1]);
      return Boolean(target && other_names.includes(target));
    };
    if (checkAgg(part_a, names_b) || checkAgg(part_b, names_a)) return true;
    return false;
  }

  /**
   * Extracts max_year, min_year, latest_pop, peak_pop, and lapse flag for an entry.
   * Note: raw populstat_cities.json populations are in thousands (pop_multiplier = 1000).
   * @param {Object} arg0_entry
   * @param {Object} [arg1_options]
   * @returns {{max_year: number|null, min_year: number|null, latest_pop: number, peak_pop: number, modern_pop: number, is_lapsed: boolean}}
   */
  function getEmpiricalPopStats (arg0_entry, arg1_options) {
    let entry = arg0_entry;
    let options = arg1_options || {};
    let mult = (options.pop_multiplier !== undefined) ? options.pop_multiplier : 1000;
    if (!entry || !entry.population || typeof entry.population !== "object")
      return { max_year: null, min_year: null, latest_pop: 0, peak_pop: 0, modern_pop: 0, is_lapsed: true };

    let yr_entries = [];
    let keys = Object.keys(entry.population);
    for (let i = 0; i < keys.length; i++) {
      let raw_yr = String(keys[i]).trim();
      let yr = (raw_yr.length >= 8 && Number(raw_yr) > 10000) ? parseInt(raw_yr.slice(0, 4), 10) : parseInt(raw_yr, 10);
      let raw_val = Array.isArray(entry.population[keys[i]]) ? entry.population[keys[i]][0] : entry.population[keys[i]];
      let val = parseFloat(raw_val)*mult;
      if (Number.isFinite(yr) && Number.isFinite(val)) yr_entries.push({ yr: yr, val: val });
    }
    yr_entries.sort((a, b) => a.yr - b.yr);
    if (yr_entries.length === 0)
      return { max_year: null, min_year: null, latest_pop: 0, peak_pop: 0, modern_pop: 0, is_lapsed: true };

    let pos = yr_entries.filter(x => x.val > 0);
    if (pos.length === 0)
      return { max_year: null, min_year: null, latest_pop: 0, peak_pop: 0, modern_pop: 0, is_lapsed: true };

    let last_all = yr_entries[yr_entries.length - 1];
    let last_pos = pos[pos.length - 1];
    let peak = 0;
    for (let i = 0; i < pos.length; i++) if (pos[i].val > peak) peak = pos[i].val;
    let modern_pos = pos.filter(x => x.yr >= 1950);
    let modern_pop = modern_pos.length > 0 ? modern_pos[modern_pos.length - 1].val : last_pos.val;

    return {
      max_year: last_pos.yr,
      min_year: pos[0].yr,
      latest_pop: Math.round(last_pos.val),
      peak_pop: Math.round(peak),
      modern_pop: Math.round(modern_pop),
      is_lapsed: (last_all.val <= 0 || entry.population["-999"] === 0)
    };
  }

  /**
   * Finds nearest GHS-UCDB urban centres within radiusKm of [lat, lng].
   * @param {Object} arg0_ctx
   * @param {number} arg1_lat
   * @param {number} arg2_lng
   * @param {number} [arg3_radius_km=20]
   * @returns {Array<Object>}
   */
  function findNearbyUCDB (arg0_ctx, arg1_lat, arg2_lng, arg3_radius_km) {
    let ctx = arg0_ctx;
    let lat = Number(arg1_lat);
    let lng = normLng(arg2_lng);
    let radius_km = (arg3_radius_km !== undefined) ? arg3_radius_km : 20;
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return [];
    let deg_r = Math.ceil(radius_km/85) + 1;
    let glat = Math.floor(lat);
    let glng = Math.floor(lng);
    let hits = [];

    for (let dlat = -deg_r; dlat <= deg_r; dlat++) {
      for (let dlng = -deg_r; dlng <= deg_r; dlng++) {
        let cell = ctx.ucdb.spatial_grid.get(`${glat + dlat},${glng + dlng}`);
        if (!cell) continue;
        for (let i = 0; i < cell.length; i++) {
          let uc = cell[i];
          let d = haversineDistanceKm([lat, lng], uc.coords);
          if (d <= radius_km) hits.push({ ucdb: uc, dist_km: Math.round(d*10)/10 });
        }
      }
    }
    hits.sort((a, b) => a.dist_km - b.dist_km);
    return hits;
  }

  /**
   * Searches GHS-UCDB for exact-name centres in compatible countries 10-800km away (plus >800km huge-country fallback).
   * @param {Object} arg0_ctx
   * @param {Object} arg1_entry
   * @param {string} arg2_country_or_key
   * @param {Object} [arg3_options]
   * @returns {Object}
   */
  function findDisplacedUCDBTwins (arg0_ctx, arg1_entry, arg2_country_or_key, arg3_options) {
    let ctx = arg0_ctx;
    let entry = arg1_entry;
    let options = arg3_options || {};
    let min_km = (options.min_km !== undefined) ? options.min_km : 10;
    let max_km = (options.max_km !== undefined) ? options.max_km : 800;
    if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2)
      return { local_match: null, displaced_twin: null, distant_twin: null };

    let names = extractAllNames(entry);
    let local_hits = findNearbyUCDB(ctx, entry.coords[0], entry.coords[1], 15);
    let local_name_hit = local_hits.find(h => h.ucdb.norm_names.some(n => names.includes(n))) || null;

    let candidates = [];
    let seen_ids = new Set();
    for (let i = 0; i < names.length; i++) {
      let matches = ctx.ucdb.by_name.get(names[i]);
      if (!matches) continue;
      for (let x = 0; x < matches.length; x++) {
        let uc = matches[x];
        if (seen_ids.has(uc.id)) continue;
        seen_ids.add(uc.id);
        if (!areCompatibleCountries(ctx, arg2_country_or_key, uc.country)) continue;
        let d = haversineDistanceKm(entry.coords, uc.coords);
        candidates.push({ ucdb: uc, dist_km: Math.round(d*10)/10 });
      }
    }
    candidates.sort((a, b) => b.ucdb.pop_ref - a.ucdb.pop_ref || a.dist_km - b.dist_km);

    let displaced = candidates.find(c => c.dist_km >= min_km && c.dist_km <= max_km) || null;
    let distant = candidates.find(c => c.dist_km > max_km) || null;
    return {
      local_any_ucdb: local_hits[0] || null,
      local_name_ucdb: local_name_hit,
      displaced_twin: displaced,
      distant_twin: distant
    };
  }

  /**
   * Computes batch-level collision clusters (<=2km) and per-country subdivision spatial medoids/spreads.
   * @param {Object} arg0_ctx
   * @param {Array<Object>} arg1_items - [{ id, raw_country_key, raw_city_key, entry }]
   * @param {Object} [arg2_options]
   * @returns {{collisions_by_id: Map<string, Object>, subdivision_stats: Map<string, Object>}}
   */
  function buildBatchSpatialStats (arg0_ctx, arg1_items, arg2_options) {
    let items = Array.isArray(arg1_items) ? arg1_items : [];
    let options = arg2_options || {};
    let collision_km = (options.collision_km !== undefined) ? options.collision_km : 2.0;

    // 1. Multi-city collisions via 0.05-deg grid bucketing
    let grid = new Map();
    let valid_items = [];
    for (let i = 0; i < items.length; i++) {
      let it = items[i];
      let c = it.entry && it.entry.coords;
      if (!Array.isArray(c) || c.length < 2) continue;
      let lat = Number(c[0]), lng = Number(c[1]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) continue;
      let gx = Math.floor(lng*20), gy = Math.floor(lat*20);
      let gk = `${gx},${gy}`;
      if (!grid.has(gk)) grid.set(gk, []);
      let rec = { idx: valid_items.length, item: it, lat: lat, lng: lng, gx: gx, gy: gy };
      valid_items.push(rec);
      grid.get(gk).push(rec);
    }

    let visited = new Uint8Array(valid_items.length);
    let collisions_by_id = new Map();
    for (let i = 0; i < valid_items.length; i++) {
      if (visited[i]) continue;
      let queue = [valid_items[i]];
      let comp = [];
      visited[i] = 1;
      while (queue.length > 0) {
        let cur = queue.pop();
        comp.push(cur);
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let peers = grid.get(`${cur.gx + dx},${cur.gy + dy}`);
            if (!peers) continue;
            for (let p = 0; p < peers.length; p++) {
              let peer = peers[p];
              if (visited[peer.idx]) continue;
              if (haversineDistanceKm([cur.lat, cur.lng], [peer.lat, peer.lng]) <= collision_km) {
                visited[peer.idx] = 1;
                queue.push(peer);
              }
            }
          }
        }
      }
      if (comp.length < 2) continue;

      // Count distinct non-agglomeration base names in component
      let distinct_groups = [];
      for (let m = 0; m < comp.length; m++) {
        let me = comp[m].item.entry;
        let matched_grp = false;
        for (let g = 0; g < distinct_groups.length; g++) {
          if (isAgglomerationOrVariantPair(distinct_groups[g][0].item.entry, me)) {
            distinct_groups[g].push(comp[m]);
            matched_grp = true;
            break;
          }
        }
        if (!matched_grp) distinct_groups.push([comp[m]]);
      }

      if (distinct_groups.length >= 2) {
        let peer_ids = comp.map(c => c.item.id);
        let peer_names = comp.map(c => c.item.entry.name || c.item.raw_city_key);
        for (let m = 0; m < comp.length; m++) {
          let cur = comp[m];
          let min_peer_km = Infinity;
          for (let p = 0; p < comp.length; p++) {
            if (p === m) continue;
            let d = haversineDistanceKm([cur.lat, cur.lng], [comp[p].lat, comp[p].lng]);
            if (d < min_peer_km) min_peer_km = d;
          }
          let same_name_peers = comp.filter(p => p !== cur && isAgglomerationOrVariantPair(p.item.entry, cur.item.entry));
          collisions_by_id.set(cur.item.id, {
            cluster_size: comp.length,
            distinct_city_count: distinct_groups.length,
            min_dist_km: Math.round(min_peer_km*100)/100,
            exact_stack: min_peer_km <= 0.1,
            peer_names: peer_names.slice(0, 12),
            peer_ids: peer_ids.slice(0, 12),
            has_same_name_twin: same_name_peers.length > 0
          });
        }
      }
    }

    // 2. Subdivision spatial stats grouped by (raw_country_key || subnational_hint)
    let sub_buckets = new Map();
    for (let i = 0; i < valid_items.length; i++) {
      let rec = valid_items[i];
      let hint = extractSubnationalHint(rec.item.entry);
      if (!hint) continue;
      let sk = `${rec.item.raw_country_key}::${hint.field}::${hint.value.toLowerCase()}`;
      if (!sub_buckets.has(sk)) sub_buckets.set(sk, []);
      sub_buckets.get(sk).push(rec);
    }

    let subdivision_stats = new Map();
    for (let [sk, pts] of sub_buckets.entries()) {
      if (pts.length < 2) continue;
      let lats = pts.map(p => p.lat).sort((a, b) => a - b);
      let lngs = pts.map(p => p.lng).sort((a, b) => a - b);
      let med_lat = lats[Math.floor(lats.length/2)];
      let med_lng = lngs[Math.floor(lngs.length/2)];
      let dists = pts.map(p => haversineDistanceKm([p.lat, p.lng], [med_lat, med_lng])).sort((a, b) => a - b);
      let p75 = dists[Math.floor(dists.length*0.75)];
      subdivision_stats.set(sk, { count: pts.length, median_coords: [med_lat, med_lng], p75_km: p75, pts: pts });
    }

    return { collisions_by_id: collisions_by_id, subdivision_stats: subdivision_stats };
  }

  /**
   * Evaluates all 7 spatial & demographic audit detectors on a single settlement entry.
   * @param {Object} arg0_ctx
   * @param {Object} arg1_item - { id, source, raw_country_key, raw_city_key, entry }
   * @param {Object} [arg2_batch_stats] - output from buildBatchSpatialStats()
   * @param {Object} [arg3_options]
   * @returns {Object} diagnostic result with { flagged, reason_codes, diagnostics }
   */
  function auditSingleEntry (arg0_ctx, arg1_item, arg2_batch_stats, arg3_options) {
    let ctx = arg0_ctx;
    let item = arg1_item;
    let stats = arg2_batch_stats;
    let options = arg3_options || {};
    let entry = item.entry || {};
    let pop_mult = (options.pop_multiplier !== undefined) ? options.pop_multiplier : (item.source === "populstat" || !item.source ? 1000 : 1);
    let pop_stats = getEmpiricalPopStats(entry, { pop_multiplier: pop_mult });
    let canonical_country = resolveCanonicalCountry(ctx, item.raw_country_key || entry.country);
    let sub_hint = extractSubnationalHint(entry);
    let reason_codes = [];
    let notes = [];

    // Detector 0/1: non-city summary junk or MISSING_OR_INVALID_COORDS
    let raw_name = String(entry.name || item.raw_city_key || "").trim();
    if (!raw_name || /^(total|inland water)\b/i.test(raw_name)) {
      reason_codes.push("MISSING_OR_INVALID_COORDS");
      notes.push(`Non-settlement summary row ("${raw_name}")`);
    }

    let coords = entry.coords;
    let lat = Array.isArray(coords) && coords.length >= 2 ? Number(coords[0]) : NaN;
    let lng = Array.isArray(coords) && coords.length >= 2 ? Number(coords[1]) : NaN;
    let has_valid_nums = Number.isFinite(lat) && Number.isFinite(lng) &&
      Math.abs(lat) <= 90 && Math.abs(lng) <= 180 && !(lat === 0 && lng === 0);

    if (!has_valid_nums) {
      if (!reason_codes.includes("MISSING_OR_INVALID_COORDS")) reason_codes.push("MISSING_OR_INVALID_COORDS");
      notes.push(`Invalid or missing coords: ${JSON.stringify(coords)}`);
      return {
        flagged: true,
        reason_codes: reason_codes,
        canonical_country: canonical_country,
        subnational_hint: sub_hint ? `${sub_hint.field}=${sub_hint.value}` : null,
        pop_stats: pop_stats,
        diagnostic_note: notes.join("; ")
      };
    }

    // Check likely swapped [lng, lat]
    let country_chk = checkCountryMembership(ctx, lat, lng, item.raw_country_key || canonical_country);
    if (!country_chk.valid && Math.abs(lng) <= 90 && Math.abs(lat) <= 180) {
      let swapped_chk = checkCountryMembership(ctx, lng, lat, item.raw_country_key || canonical_country);
      if (swapped_chk.valid) {
        if (!reason_codes.includes("MISSING_OR_INVALID_COORDS")) reason_codes.push("MISSING_OR_INVALID_COORDS");
        notes.push(`Likely swapped [lng,lat]: [${lat}, ${lng}] -> [${lng}, ${lat}]`);
      }
    }

    // Detector 2: COUNTRY_MISMATCH
    if (!country_chk.valid) {
      reason_codes.push("COUNTRY_MISMATCH");
      notes.push(`Outside ${canonical_country} by ${country_chk.dist_km}km (at: ${country_chk.actual_countries_at_point.join(",") || "ocean"})`);
    } else if (country_chk.dependency_mismatch) {
      notes.push(`Dependency territory note: matched ${country_chk.matched_admin}`);
    }

    // Detector 6 prep & UCDB lookups
    let ghs = sampleGHSPop(ctx, lat, lng);
    let ucdb_info = findDisplacedUCDBTwins(ctx, entry, item.raw_country_key || canonical_country);
    let has_local_ucdb_name = Boolean(ucdb_info.local_name_ucdb);
    let has_local_ucdb_any = Boolean(ucdb_info.local_any_ucdb);

    // Detector 3: MULTI_CITY_COLLISION
    let collision = stats && stats.collisions_by_id ? stats.collisions_by_id.get(item.id) : null;
    if (collision) {
      reason_codes.push("MULTI_CITY_COLLISION");
      notes.push(`Collides within 2km with ${collision.distinct_city_count} distinct cities (${collision.peer_names.slice(0, 4).join(", ")})`);
    }

    // Detector 4: COUNTRY_CENTROID_FALLBACK
    let cent_chk = checkCountryCentroidProximity(ctx, lat, lng, item.raw_country_key || canonical_country);
    if (cent_chk.near_centroid) {
      let is_real_core_at_centroid = has_local_ucdb_name ||
        (!collision && pop_stats.modern_pop > 0 && ghs.ghs_max_3x3 >= 0.35*pop_stats.modern_pop);
      if (!is_real_core_at_centroid) {
        reason_codes.push("COUNTRY_CENTROID_FALLBACK");
        notes.push(`Within ${cent_chk.min_dist_km}km of ${canonical_country} ${cent_chk.centroid_type} centroid`);
      }
    }

    // Detector 5: SUBDIVISION_MISMATCH_OR_CENTROID
    let sub_flagged = false;
    if (String(item.raw_country_key || "").toLowerCase().startsWith("usas-")) {
      let st_chk = checkUSState(lat, lng, item.raw_country_key);
      if (!st_chk.valid) {
        sub_flagged = true;
        notes.push(`Outside US state ${st_chk.state_name} bbox by ${st_chk.dist_to_bbox_km}km`);
      } else if (st_chk.at_state_centroid && !has_local_ucdb_name && ghs.ghs_max_3x3 < 0.30*Math.max(1, pop_stats.modern_pop)) {
        sub_flagged = true;
        notes.push(`Within ${st_chk.dist_to_centroid_km}km of ${st_chk.state_name} state centroid`);
      }
    }
    if (entry.position) {
      let pos_coords = parsePopulstatPosition(entry.position, coords);
      if (pos_coords) {
        let pos_dist = haversineDistanceKm(coords, pos_coords);
        if (pos_dist > 150 && !has_local_ucdb_name && ghs.ghs_max_3x3 < 0.25*Math.max(1, pop_stats.modern_pop)) {
          sub_flagged = true;
          notes.push(`Populstat position (${pos_coords[0].toFixed(2)},${pos_coords[1].toFixed(2)}) is ${Math.round(pos_dist)}km from coords`);
        }
      }
    }
    if (sub_hint && stats && stats.subdivision_stats) {
      let sk = `${item.raw_country_key}::${sub_hint.field}::${sub_hint.value.toLowerCase()}`;
      let sstat = stats.subdivision_stats.get(sk);
      if (sstat && sstat.count >= 3) {
        let nearest_peer = Infinity;
        for (let p = 0; p < sstat.pts.length; p++) {
          let pt = sstat.pts[p];
          if (pt.item.id === item.id) continue;
          let dp = haversineDistanceKm(coords, [pt.lat, pt.lng]);
          if (dp < nearest_peer) nearest_peer = dp;
        }
        let d_med = haversineDistanceKm(coords, sstat.median_coords);
        if (d_med > Math.max(150, 2.5*sstat.p75_km) && nearest_peer > 100) {
          sub_flagged = true;
          notes.push(`Subdivision ${sub_hint.field}=${sub_hint.value} outlier (${Math.round(d_med)}km from cluster median, nearest peer ${Math.round(nearest_peer)}km)`);
        }
      }
      // Homonymous city == subdivision rural centroid check
      if (normaliseName(raw_name) === normaliseName(sub_hint.value) && pop_stats.modern_pop >= 5000 &&
          !has_local_ucdb_name && ghs.ghs_max_3x3 < 0.25*pop_stats.modern_pop) {
        sub_flagged = true;
        notes.push(`Homonymous city==subdivision (${sub_hint.value}) at low-density coords (ghs=${Math.round(ghs.ghs_max_3x3)} vs ${pop_stats.modern_pop})`);
      }
    }
    if (sub_flagged) reason_codes.push("SUBDIVISION_MISMATCH_OR_CENTROID");

    // Detector 6: URBAN_VACUUM_2000_2025
    let p_emp = pop_stats.modern_pop;
    let is_modern = !pop_stats.is_lapsed && pop_stats.max_year !== null && pop_stats.max_year >= 1950;
    let is_microstate = Boolean(ARCHIPELAGO_BOUNDS[canonical_country]) || Boolean(country_chk.inside_archipelago);
    let vacuum_hit = false;
    if (is_modern && p_emp > 0) {
      let vac_50k = (p_emp >= 50000 && ghs.ghs_max_3x3 < 0.20*p_emp);
      let vac_15k = (p_emp >= 15000 && ghs.ghs_max_3x3 < 0.12*p_emp);
      let vac_3k = (p_emp >= 3000 && ghs.ghs_max_3x3 < 250);
      let vac_water = (ghs.land_3x3 === 0 && ghs.ghs_max_3x3 < 250 && !is_microstate);
      if (vac_50k || vac_15k || vac_3k || vac_water) {
        let is_county_seat_ok = (canonical_country === "China" || canonical_country === "India" || canonical_country === "Japan") &&
          (has_local_ucdb_name || (has_local_ucdb_any && ghs.ghs_max_3x3 >= 50000)) &&
          !sub_flagged && !collision && !cent_chk.near_centroid;
        if (!is_county_seat_ok) {
          vacuum_hit = true;
          reason_codes.push("URBAN_VACUUM_2000_2025");
          notes.push(`Urban vacuum: P_emp=${p_emp}, ghs2000_3x3=${Math.round(ghs.ghs2000_3x3)}, ghs2025_3x3=${Math.round(ghs.ghs2025_3x3)}, land3x3=${ghs.land_3x3}`);
        }
      }
    }

    // Detector 7: DISPLACED_UCDB_TWIN
    let twin = ucdb_info.displaced_twin ||
      ((ucdb_info.distant_twin && (vacuum_hit || sub_flagged || ghs.ghs_max_3x3 < 0.15*Math.max(1, p_emp))) ? ucdb_info.distant_twin : null);
    if (twin && !has_local_ucdb_name) {
      let primary_city_norm = normaliseName(raw_name);
      let twin_main_norm = normaliseName(twin.ucdb.name);
      let is_primary_name_twin = Boolean(primary_city_norm && twin_main_norm && primary_city_norm === twin_main_norm);
      let low_local_pop = (p_emp > 0) ? (ghs.ghs_max_3x3 < 0.15*p_emp) : (!has_local_ucdb_any && ghs.ghs_max_3x3 < 5000);
      let displaced_cond = low_local_pop ||
        (!has_local_ucdb_any && ghs.ghs_max_3x3 < 0.25*Math.max(1, p_emp) && (is_primary_name_twin || vacuum_hit || cent_chk.near_centroid || sub_flagged || !country_chk.valid));
      if (displaced_cond && (twin.dist_km <= 800 || vacuum_hit || sub_flagged || !country_chk.valid || cent_chk.near_centroid)) {
        reason_codes.push("DISPLACED_UCDB_TWIN");
        notes.push(`UCDB twin "${twin.ucdb.name}" (${twin.ucdb.country}, pop=${twin.ucdb.pop_ref}) is ${twin.dist_km}km away at [${twin.ucdb.coords[0].toFixed(4)},${twin.ucdb.coords[1].toFixed(4)}]`);
      }
    }

    return {
      flagged: reason_codes.length > 0,
      reason_codes: reason_codes,
      canonical_country: canonical_country,
      subnational_hint: sub_hint ? `${sub_hint.field}=${sub_hint.value}` : null,
      pop_stats: pop_stats,
      ghs: ghs,
      country_check: country_chk,
      centroid_check: cent_chk,
      ucdb_info: ucdb_info,
      collision: collision,
      diagnostic_note: notes.join("; ")
    };
  }

  module.exports = {
    ARCHIPELAGO_BOUNDS: ARCHIPELAGO_BOUNDS,
    COUNTRY_ALIASES: COUNTRY_ALIASES,
    GOOGLE_CENTROIDS: GOOGLE_CENTROIDS,
    PATHS: PATHS,
    TERRITORY_RULES: TERRITORY_RULES,
    US_STATE_BOUNDS: US_STATE_BOUNDS,
    areCompatibleCountries: areCompatibleCountries,
    auditSingleEntry: auditSingleEntry,
    buildBatchSpatialStats: buildBatchSpatialStats,
    checkCountryCentroidProximity: checkCountryCentroidProximity,
    checkCountryMembership: checkCountryMembership,
    checkUSState: checkUSState,
    coordsToPixel: coordsToPixel,
    distanceToBoxKm: distanceToBoxKm,
    distanceToGeometryKm: distanceToGeometryKm,
    extractAllNames: extractAllNames,
    extractSubnationalHint: extractSubnationalHint,
    findDisplacedUCDBTwins: findDisplacedUCDBTwins,
    findNearbyUCDB: findNearbyUCDB,
    getEmpiricalPopStats: getEmpiricalPopStats,
    haversineDistanceKm: haversineDistanceKm,
    isAgglomerationOrVariantPair: isAgglomerationOrVariantPair,
    loadAuditContext: loadAuditContext,
    normLng: normLng,
    normaliseName: normaliseName,
    parsePopulstatPosition: parsePopulstatPosition,
    parseSemicolonCSVLine: parseSemicolonCSVLine,
    pointInBox: pointInBox,
    pointInGeometry: pointInGeometry,
    pointInRing: pointInRing,
    readFloat32Raster: readFloat32Raster,
    readUint32Raster: readUint32Raster,
    resolveCanonicalCountry: resolveCanonicalCountry,
    sampleGHSPop: sampleGHSPop,
    sampleIso2: sampleIso2,
    sampleRaster3x3: sampleRaster3x3
  };
}
