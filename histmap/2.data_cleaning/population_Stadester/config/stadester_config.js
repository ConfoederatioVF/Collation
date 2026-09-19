//Initialise functions
{
  if (!global.population_Stadester_config) global.population_Stadester_config = {};
  
  global.population_Stadester_config = {
    baseline_year: 1800,
    cutoff_year: 1975,
    deg_to_radians: Math.PI/180,
    earth_radius: 6371,
    end_year: 2000,
    pixel_deg: 5/60,
    area_to_pop_growth_rate_ratio: 1.27,
    stadester_y_offset: -1,
    uud_domain: [-3000, 2025],
    
    baseline_density_per_ha: [175, 190],
    angel_density_change_per_decade: {
      "1810": -0.0036,
      "1820": 0.0001,
      "1830": -0.0003,
      "1840": -0.0009,
      "1850": 0.0057,
      "1860": 0.0025,
      "1870": 0.0045,
      "1880": 0.0029,
      "1890": -0.0016,
      "1900": -0.0084,
      "1910": -0.0098,
      "1920": -0.0154,
      "1930": -0.0138,
      "1940": -0.0052,
      "1950": -0.0059,
      "1960": -0.0127,
      "1969": -0.0084,
      "1980": -0.0083,
      "1990": -0.0103,
      "2000": -0.0096
    },
    
    regions: {
      northern_america: { colour: [87, 122, 175], name: "Northern America" },
      latin_america: { colour: [71, 165, 101], name: "Latin America" },
      europe: { colour: [47, 97, 170], name: "Europe" },
      eastern_europe_and_russia: { colour: [20, 114, 30], name: "Eastern Europe and Russia" },
      central_asia: { colour: [41, 193, 175], name: "Central Asia" },
      middle_east: { colour: [198, 130, 129], name: "Middle East" },
      maghreb_egypt: { colour: [239, 188, 112], name: "Maghreb and Egypt" },
      sub_saharan_africa: { colour: [155, 101, 77], name: "Sub-Saharan Africa" },
      oceania: { colour: [0, 205, 143], name: "Oceania" },
      indian_subcontinent: { colour: [214, 144, 83], name: "Indian Subcontinent" },
      southeast_asia: { colour: [97, 144, 163], name: "Southeast Asia" },
      eastasia: { colour: [173, 62, 62], name: "East Asia" }
    },
    
    angel_regions: {
      east_asia: {
        colour: [214, 144, 83],
        cities: {
          bangkok: { "1800": 1.5, "1900": 1.6, "1922": 1.7, "1953": 1.5, "1988": 2.0 },
          beijing: { "1800": 1.5, "1900": 1.4, "1929": 1.6, "1959": 1.7, "1988": 1.8 },
          kolkata: { "1800": 1.4, "1883": 1.7, "1931": 1.8, "1961": 1.6, "1990": 1.7 },
          manila: { "1800": 1.4, "1898": 1.5, "1945": 1.7, "1971": 1.6, "1990": 1.7 },
          mumbai: { "1800": 1.5, "1902": 1.6, "1931": 1.5, "1968": 1.5, "1991": 1.8 },
          shanghai: { "1800": 1.4, "1902": 1.5, "1944": 1.4, "1973": 1.8, "1991": 1.7 }
        }
      },
      eu_and_japan: {
        colour: [47, 97, 170],
        cities: {
          london: { "1800": 1.6, "1880": 1.9, "1929": 1.6, "1955": 1.7, "1989": 1.7 },
          moscow: { "1800": 1.7, "1893": 1.6, "1939": 1.6, "1957": 1.6, "1991": 2.1 },
          paris: { "1800": 1.5, "1900": 1.6, "1928": 1.6, "1956": 1.8, "1987": 1.6 },
          tokyo: { "1800": 1.4, "1892": 1.4, "1929": 1.5, "1954": 1.6, "1990": 1.4 },
          warsaw: { "1800": 1.6, "1888": 1.6, "1936": 1.6, "1958": 1.5, "1992": 1.6 }
        }
      },
      mena: {
        colour: [239, 188, 112],
        cities: {
          algiers: { "1800": 1.4, "1903": 1.6, "1929": 1.9, "1972": 1.7, "1987": 1.7 },
          cairo: { "1800": 1.5, "1897": 1.6, "1927": 1.6, "1960": 1.6, "1992": 1.7 },
          istanbul: { "1800": 1.6, "1899": 1.8, "1934": 1.8, "1960": 1.7, "1990": 2.0 },
          jeddah: { "1800": 1.9, "1900": 1.7, "1925": 1.5, "1964": 1.6, "1990": 1.7 },
          kuwait: { "1800": 1.6, "1900": 2.1, "1922": 1.8, "1963": 2.0, "1990": 2.1 },
          tehran: { "1800": 1.5, "1849": 1.4, "1925": 1.5, "1956": 1.5, "1991": 1.9 },
          tel_aviv: { "1800": 1.4, "1917": 1.4, "1929": 1.5, "1956": 1.6, "1987": 2.0 }
        }
      },
      latin_america: {
        colour: [186, 80, 80],
        cities: {
          buenos_aires: { "1800": 1.3, "1887": 1.4, "1918": 1.4, "1964": 1.5, "1989": 1.6 },
          guatemala: { "1800": 1.5, "1900": 1.4, "1936": 1.6, "1976": 1.7, "1990": 1.9 },
          mexico: { "1800": 1.4, "1886": 1.4, "1929": 1.5, "1970": 1.7, "1990": 1.7 },
          santiago: { "1800": 1.4, "1900": 1.5, "1930": 1.5, "1970": 1.7, "1990": 2.0 },
          sao_paulo: { "1800": 1.5, "1905": 1.6, "1929": 1.7, "1974": 1.7, "1988": 1.7 }
        }
      },
      lrdc: {
        colour: [20, 114, 30],
        cities: {
          chicago: { "1800": 1.5, "1893": 1.5, "1945": 1.6, "1967": 1.6, "1989": 1.7 },
          los_angeles: { "1800": 1.7, "1907": 1.4, "1937": 1.7, "1970": 1.8, "1990": 2.0 },
          sydney: { "1800": 1.5, "1895": 1.7, "1945": 1.8, "1975": 1.7, "1991": 1.8 }
        }
      },
      sub_saharan_africa: {
        colour: [47, 114, 142],
        cities: {
          accra: { "1800": 1.6, "1903": 1.6, "1929": 1.8, "1956": 1.5, "1991": 1.7 },
          johannesburg: { "1800": 1.5, "1900": 1.7, "1938": 1.6, "1957": 1.7, "1990": 2.3 },
          lagos: { "1800": 1.4, "1900": 1.6, "1920": 1.6, "1962": 1.8, "1984": 1.8 },
          nairobi: { "1800": 2.0, "1906": 1.6, "1926": 1.5, "1964": 1.5, "1988": 1.6 }
        }
      }
    },
    
    clark_equations: {
      "1800": {
        default: function (arg0_options) {
          //Convert from parameters
          let options = (arg0_options) ? arg0_options : {};
          
          //Declare local instance variables
          let A = options.A*100;
          let b = options.b;
          let x = options.x;
          
          //Return statement
          return A*Math.exp(-b*x);
        }
      },
      "1945": {
        anglo_settler: function (arg0_options) {
          //Convert from parameters
          let options = (arg0_options) ? arg0_options : {};
          
          //Declare local instance variables
          let A = options.A*100;
          let b = options.b;
          let x = options.x;
          
          //Return statement
          return A*x*Math.exp(-0.067*x);
        },
        eu_and_east_asia: function (arg0_options) {
          //Convert from parameters
          let options = (arg0_options) ? arg0_options : {};
          
          //Declare local instance variables
          let A = options.A*100;
          let b = options.b;
          let x = options.x;
          
          //Return statement
          return A*(x + 0.5)*Math.exp(-b*x);
        },
        global_south: function (arg0_options) {
          //Convert from parameters
          let options = (arg0_options) ? arg0_options : {};
          
          //Declare local instance variables
          let A = options.A*100;
          let b = options.b;
          let x = options.x;
          
          //Return statement
          return A*Math.exp(-b*x);
        },
        socialist_world: function (arg0_options) {
          //Convert from parameters
          let options = (arg0_options) ? arg0_options : {};
          
          //Declare local instance variables
          let x = options.x;
          
          //Return statement
          return 1/(1 + Math.exp(4*(x - 1.8)));
        }
      }
    },
    
    populstat_countries: {
      afghani: 'Afghanistan', bahrain: 'Bahrain', banglad: 'Bangladesh', bhutan: 'Bhutan', brunei: 'Brunei',
      cambodi: 'Cambodia', china: 'China', cyprus: 'Cyprus', easttim: 'East Timor', hongkon: 'Hong Kong',
      india: 'India', indones: 'Indonesia', iran: 'Iran', iraq: 'Iraq', israel: 'Israel', japan: 'Japan',
      jordan: 'Jordan', kazakhs: 'Kazakhstan', kuwait: 'Kuwait', kyrgyzs: 'Kyrgyzstan', laos: 'Laos',
      lebanon: 'Lebanon', malaysi: 'Malaysia', maldive: 'Maldives', mongoli: 'Mongolia', myanmar: 'Myanmar',
      nepal: 'Nepal', nkorea: 'North Korea', oman: 'Oman', pakista: 'Pakistan', palesti: 'Palestine',
      philipp: 'Philippines', qatar: 'Qatar', saudiar: 'Saudi Arabia', singapo: 'Singapore', skorea: 'South Korea',
      srilank: 'Sri Lanka', syria: 'Syria', taiwan: 'Taiwan', tajikis: 'Tajikistan', thailan: 'Thailand',
      turkey: 'Turkey', turkmen: 'Turkmenistan', unarabe: 'United Arab Emirates', uzbekis: 'Uzbekistan',
      vietnam: 'Vietnam', yemen: 'Yemen', albania: 'Albania', andorra: 'Andorra', armenia: 'Armenia',
      austria: 'Austria', azerbai: 'Azerbaijan', belarus: 'Belarus', belgium: 'Belgium', bosniah: 'Bosnia and Herzegovina',
      bulgari: 'Bulgaria', croatia: 'Croatia', czechrp: 'Czech Republic', denmark: 'Denmark', estonia: 'Estonia',
      finland: 'Finland', france: 'France', georgia: 'Georgia', germany: 'Germany', greece: 'Greece',
      hungary: 'Hungary', iceland: 'Iceland', ireland: 'Ireland', italy: 'Italy', kosovo: 'Kosovo',
      latvia: 'Latvia', liechte: 'Liechtenstein', lithuan: 'Lithuania', luxembu: 'Luxembourg', macedon: 'Macedonia',
      malta: 'Malta', moldova: 'Moldova', monaco: 'Monaco', montene: 'Montenegro', netherl: 'Netherlands',
      norway: 'Norway', poland: 'Poland', portuga: 'Portugal', romania: 'Romania', russia: 'Russia',
      sanmari: 'San Marino', serbia: 'Serbia', slovaki: 'Slovakia', sloveni: 'Slovenia', spain: 'Spain',
      sweden: 'Sweden', switzer: 'Switzerland', ukraine: 'Ukraine', unitedk: 'United Kingdom', vatican: 'Vatican City',
      algeria: 'Algeria', angola: 'Angola', benin: 'Benin', botswan: 'Botswana', burkina: 'Burkina Faso',
      burundi: 'Burundi', cameroo: 'Cameroon', capever: 'Cape Verde', car: 'Central African Republic',
      chad: 'Chad', comoros: 'Comoros', congo: 'Republic of the Congo', drc: 'Democratic Republic of the Congo',
      djibout: 'Djibouti', egypt: 'Egypt', eqguine: 'Equatorial Guinea', eritrea: 'Eritrea', eswatin: 'Eswatini',
      ethiopi: 'Ethiopia', gabon: 'Gabon', gambia: 'Gambia', ghana: 'Ghana', guinea: 'Guinea', guineab: 'Guinea-Bissau',
      ivoryco: 'Ivory Coast', kenya: 'Kenya', lesotho: 'Lesotho', liberia: 'Liberia', libya: 'Libya',
      madagas: 'Madagascar', malawi: 'Malawi', mali: 'Mali', maurita: 'Mauritania', mauriti: 'Mauritius',
      morocco: 'Morocco', mozambi: 'Mozambique', namibia: 'Namibia', niger: 'Niger', nigeria: 'Nigeria',
      rwanda: 'Rwanda', saotome: 'Sao Tome and Principe', senegal: 'Senegal', seychel: 'Seychelles',
      sierral: 'Sierra Leone', somalia: 'Somalia', southaf: 'South Africa', ssudan: 'South Sudan',
      sudan: 'Sudan', tanzani: 'Tanzania', togo: 'Togo', tunisia: 'Tunisia', uganda: 'Uganda',
      zambia: 'Zambia', zimbabw: 'Zimbabwe', canada: 'Canada', mexicoc: 'Mexico', uniteds: 'United States of America',
      antigua: 'Antigua and Barbuda', bahamas: 'Bahamas', barbado: 'Barbados', belize: 'Belize',
      costari: 'Costa Rica', cuba: 'Cuba', dominic: 'Dominica', dominrp: 'Dominican Republic',
      elsalva: 'El Salvador', grenada: 'Grenada', guatema: 'Guatemala', haiti: 'Haiti', hondura: 'Honduras',
      jamaica: 'Jamaica', nicarag: 'Nicaragua', panama: 'Panama', stkitts: 'Saint Kitts and Nevis',
      stlucia: 'Saint Lucia', stvince: 'Saint Vincent and the Grenadines', trinidad: 'Trinidad and Tobago',
      argenti: 'Argentina', bolivia: 'Bolivia', brazil: 'Brazil', chile: 'Chile', colombi: 'Colombia',
      ecuador: 'Ecuador', guyana: 'Guyana', paragua: 'Paraguay', peru: 'Peru', surinam: 'Suriname',
      uruguay: 'Uruguay', venezue: 'Venezuela', austral: 'Australia', fiji: 'Fiji', kiribat: 'Kiribati',
      marshal: 'Marshall Islands', microne: 'Micronesia', nauru: 'Nauru', newzeal: 'New Zealand',
      palau: 'Palau', papuane: 'Papua New Guinea', samoa: 'Samoa', solomon: 'Solomon Islands',
      tonga: 'Tonga', tuvalu: 'Tuvalu', vanuatu: 'Vanuatu'
    },
    
    whitelisted_cities: [
      "Adana-Turkey", "Alexandria-Egypt", "Amarapura-Myanmar", "Augsburg-Germany", "Basra-Iraq",
      "Bussa-Nigeria", "Beijing-China", "Birmingham-United States of America", "Changchun-China",
      "Changzhou-China", "Chongqing-China", "Cincinnati-United States of America", "Cochin-India",
      "Curitiba-Brazil", "Datong-China", "Delhi-India", "Esfahan-Iran", "Genova-Italy",
      "Hefei-China", "Houston-United States of America", "Inwa-Myanmar", "Izmail-Ukraine",
      "Kashi-China", "Leshan-China", "Louisville-United States of America", "Luanda-Angola",
      "Luoyang-China", "Madrid-Spain", "Malaga-Spain", "Meerut-India", "Melbourne-Australia",
      "Mumbai-India", "Nanning-China", "New Orleans-United States of America", "Oran-Algeria",
      "Osaka-Japan", "Padang-Indonesia", "Pekalongan-Indonesia", "Pittsburgh-United States of America",
      "Potosi-Bolivia", "Poznan-Poland", "Qiqihar-China", "Samarkand-Uzbekistan", "Skopje-Macedonia",
      "Sydney-Australia", "Taian-China", "Taiyuan-China", "Tarsus-Turkey", "Tehran-Iran",
      "Tokyo-Japan", "Tripoli-Libya", "Urumqi-China", "Vishakhapatnam-India", "Wuzhou-China",
      "Xingtai-China", "Srirangapatna-India", "St. Louis-United States of America", "Visakhapatnam-India"
    ]
  };
}
