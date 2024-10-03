"""Astral geocoder is a database of locations stored within the package.

To get the :class:`~astral.LocationInfo` for a location use the
:func:`~astral.geocoder.lookup` function e.g. ::

    from astral.geocoder import lookup, database
    l = lookup("London", database())

All locations stored in the database can be accessed using the `all_locations` generator ::

    from astral.geocoder import all_locations
    for location in all_locations:
        print(location)
"""

from functools import reduce
from typing import Dict, Generator, List, Optional, Tuple, Union

from astral import LocationInfo, dms_to_float

__all__ = ["lookup", "database", "add_locations", "all_locations"]


# region Location Info
# name,region,timezone,latitude,longitude,elevation
_LOCATION_INFO = """Abu Dhabi,UAE,Asia/Dubai,24°28'N,54°22'E
Abu Dhabi,United Arab Emirates,Asia/Dubai,24°28'N,54°22'E
Abuja,Nigeria,Africa/Lagos,09°05'N,07°32'E
Accra,Ghana,Africa/Accra,05°35'N,00°06'W
Addis Ababa,Ethiopia,Africa/Addis_Ababa,09°02'N,38°42'E
Adelaide,Australia,Australia/Adelaide,34°56'S,138°36'E
Al Jubail,Saudi Arabia,Asia/Riyadh,25°24'N,49°39'W
Algiers,Algeria,Africa/Algiers,36°42'N,03°08'E
Amman,Jordan,Asia/Amman,31°57'N,35°52'E
Amsterdam,Netherlands,Europe/Amsterdam,52°23'N,04°54'E
Andorra la Vella,Andorra,Europe/Andorra,42°31'N,01°32'E
Ankara,Turkey,Europe/Istanbul,39°57'N,32°54'E
Antananarivo,Madagascar,Indian/Antananarivo,18°55'S,47°31'E
Apia,Samoa,Pacific/Apia,13°50'S,171°50'W
Ashgabat,Turkmenistan,Asia/Ashgabat,38°00'N,57°50'E
Asmara,Eritrea,Africa/Asmara,15°19'N,38°55'E
Astana,Kazakhstan,Asia/Qyzylorda,51°10'N,71°30'E
Asuncion,Paraguay,America/Asuncion,25°10'S,57°30'W
Athens,Greece,Europe/Athens,37°58'N,23°46'E
Avarua,Cook Islands,Etc/GMT-10,21°12'N,159°46'W
Baghdad,Iraq,Asia/Baghdad,33°20'N,44°30'E
Baku,Azerbaijan,Asia/Baku,40°29'N,49°56'E
Bamako,Mali,Africa/Bamako,12°34'N,07°55'W
Bandar Seri Begawan,Brunei Darussalam,Asia/Brunei,04°52'N,115°00'E
Bangkok,Thailand,Asia/Bangkok,13°45'N,100°35'E
Bangui,Central African Republic,Africa/Bangui,04°23'N,18°35'E
Banjul,Gambia,Africa/Banjul,13°28'N,16°40'W
Basse-Terre,Guadeloupe,America/Guadeloupe,16°00'N,61°44'W
Basseterre,Saint Kitts and Nevis,America/St_Kitts,17°17'N,62°43'W
Beijing,China,Asia/Harbin,39°55'N,116°20'E
Beirut,Lebanon,Asia/Beirut,33°53'N,35°31'E
Belfast,Northern Ireland,Europe/Belfast,54°36'N,5°56'W
Belgrade,Yugoslavia,Europe/Belgrade,44°50'N,20°37'E
Belmopan,Belize,America/Belize,17°18'N,88°30'W
Berlin,Germany,Europe/Berlin,52°30'N,13°25'E
Bern,Switzerland,Europe/Zurich,46°57'N,07°28'E
Bishkek,Kyrgyzstan,Asia/Bishkek,42°54'N,74°46'E
Bissau,Guinea-Bissau,Africa/Bissau,11°45'N,15°45'W
Bloemfontein,South Africa,Africa/Johannesburg,29°12'S,26°07'E
Bogota,Colombia,America/Bogota,04°34'N,74°00'W
Brasilia,Brazil,Brazil/East,15°47'S,47°55'W
Bratislava,Slovakia,Europe/Bratislava,48°10'N,17°07'E
Brazzaville,Congo,Africa/Brazzaville,04°09'S,15°12'E
Bridgetown,Barbados,America/Barbados,13°05'N,59°30'W
Brisbane,Australia,Australia/Brisbane,27°30'S,153°01'E
Brussels,Belgium,Europe/Brussels,50°51'N,04°21'E
Bucharest,Romania,Europe/Bucharest,44°27'N,26°10'E
Bucuresti,Romania,Europe/Bucharest,44°27'N,26°10'E
Budapest,Hungary,Europe/Budapest,47°29'N,19°05'E
Buenos Aires,Argentina,America/Buenos_Aires,34°62'S,58°44'W
Bujumbura,Burundi,Africa/Bujumbura,03°16'S,29°18'E
Cairo,Egypt,Africa/Cairo,30°01'N,31°14'E
Canberra,Australia,Australia/Canberra,35°15'S,149°08'E
Cape Town,South Africa,Africa/Johannesburg,33°55'S,18°22'E
Caracas,Venezuela,America/Caracas,10°30'N,66°55'W
Castries,Saint Lucia,America/St_Lucia,14°02'N,60°58'W
Cayenne,French Guiana,America/Cayenne,05°05'N,52°18'W
Charlotte Amalie,United States of Virgin Islands,America/Virgin,18°21'N,64°56'W
Chisinau,Moldova,Europe/Chisinau,47°02'N,28°50'E
Conakry,Guinea,Africa/Conakry,09°29'N,13°49'W
Copenhagen,Denmark,Europe/Copenhagen,55°41'N,12°34'E
Cotonou,Benin,Africa/Porto-Novo,06°23'N,02°42'E
Dakar,Senegal,Africa/Dakar,14°34'N,17°29'W
Damascus,Syrian Arab Republic,Asia/Damascus,33°30'N,36°18'E
Dammam,Saudi Arabia,Asia/Riyadh,26°30'N,50°12'E
Darwin,Australia,Australia/Darwin,12°26'S,130°50'E
Dhaka,Bangladesh,Asia/Dhaka,23°43'N,90°26'E
Dili,East Timor,Asia/Dili,08°29'S,125°34'E
Djibouti,Djibouti,Africa/Djibouti,11°08'N,42°20'E
Dodoma,United Republic of Tanzania,Africa/Dar_es_Salaam,06°08'S,35°45'E
Doha,Qatar,Asia/Qatar,25°15'N,51°35'E
Douglas,Isle Of Man,Europe/London,54°9'N,4°29'W
Dublin,Ireland,Europe/Dublin,53°21'N,06°15'W
Dushanbe,Tajikistan,Asia/Dushanbe,38°33'N,68°48'E
El Aaiun,Morocco,UTC,27°9'N,13°12'W
Fort-de-France,Martinique,America/Martinique,14°36'N,61°02'W
Freetown,Sierra Leone,Africa/Freetown,08°30'N,13°17'W
Funafuti,Tuvalu,Pacific/Funafuti,08°31'S,179°13'E
Gaborone,Botswana,Africa/Gaborone,24°45'S,25°57'E
George Town,Cayman Islands,America/Cayman,19°20'N,81°24'W
Georgetown,Guyana,America/Guyana,06°50'N,58°12'W
Gibraltar,Gibraltar,Europe/Gibraltar,36°9'N,5°21'W
Guatemala,Guatemala,America/Guatemala,14°40'N,90°22'W
Hanoi,Viet Nam,Asia/Saigon,21°05'N,105°55'E
Harare,Zimbabwe,Africa/Harare,17°43'S,31°02'E
Havana,Cuba,America/Havana,23°08'N,82°22'W
Helsinki,Finland,Europe/Helsinki,60°15'N,25°03'E
Hobart,Tasmania,Australia/Hobart,42°53'S,147°19'E
Hong Kong,China,Asia/Hong_Kong,22°16'N,114°09'E
Honiara,Solomon Islands,Pacific/Guadalcanal,09°27'S,159°57'E
Islamabad,Pakistan,Asia/Karachi,33°40'N,73°10'E
Jakarta,Indonesia,Asia/Jakarta,06°09'S,106°49'E
Jerusalem,Israel,Asia/Jerusalem,31°47'N,35°12'E
Juba,South Sudan,Africa/Juba,4°51'N,31°36'E
Jubail,Saudi Arabia,Asia/Riyadh,27°02'N,49°39'E
Kabul,Afghanistan,Asia/Kabul,34°28'N,69°11'E
Kampala,Uganda,Africa/Kampala,00°20'N,32°30'E
Kathmandu,Nepal,Asia/Kathmandu,27°45'N,85°20'E
Khartoum,Sudan,Africa/Khartoum,15°31'N,32°35'E
Kiev,Ukraine,Europe/Kiev,50°30'N,30°28'E
Kigali,Rwanda,Africa/Kigali,01°59'S,30°04'E
Kingston,Jamaica,America/Jamaica,18°00'N,76°50'W
Kingston,Norfolk Island,Pacific/Norfolk,45°20'S,168°43'E
Kingstown,Saint Vincent and the Grenadines,America/St_Vincent,13°10'N,61°10'W
Kinshasa,Democratic Republic of the Congo,Africa/Kinshasa,04°20'S,15°15'E
Koror,Palau,Pacific/Palau,07°20'N,134°28'E
Kuala Lumpur,Malaysia,Asia/Kuala_Lumpur,03°09'N,101°41'E
Kuwait,Kuwait,Asia/Kuwait,29°30'N,48°00'E
La Paz,Bolivia,America/La_Paz,16°20'S,68°10'W
Libreville,Gabon,Africa/Libreville,00°25'N,09°26'E
Lilongwe,Malawi,Africa/Blantyre,14°00'S,33°48'E
Lima,Peru,America/Lima,12°00'S,77°00'W
Lisbon,Portugal,Europe/Lisbon,38°42'N,09°10'W
Ljubljana,Slovenia,Europe/Ljubljana,46°04'N,14°33'E
Lome,Togo,Africa/Lome,06°09'N,01°20'E
London,England,Europe/London,51°28'24"N,00°00'3"W
Luanda,Angola,Africa/Luanda,08°50'S,13°15'E
Lusaka,Zambia,Africa/Lusaka,15°28'S,28°16'E
Luxembourg,Luxembourg,Europe/Luxembourg,49°37'N,06°09'E
Macau,Macao,Asia/Macau,22°12'N,113°33'E
Madinah,Saudi Arabia,Asia/Riyadh,24°28'N,39°36'E
Madrid,Spain,Europe/Madrid,40°25'N,03°45'W
Majuro,Marshall Islands,Pacific/Majuro,7°4'N,171°16'E
Makkah,Saudi Arabia,Asia/Riyadh,21°26'N,39°49'E
Malabo,Equatorial Guinea,Africa/Malabo,03°45'N,08°50'E
Male,Maldives,Indian/Maldives,04°00'N,73°28'E
Mamoudzou,Mayotte,Indian/Mayotte,12°48'S,45°14'E
Managua,Nicaragua,America/Managua,12°06'N,86°20'W
Manama,Bahrain,Asia/Bahrain,26°10'N,50°30'E
Manila,Philippines,Asia/Manila,14°40'N,121°03'E
Maputo,Mozambique,Africa/Maputo,25°58'S,32°32'E
Maseru,Lesotho,Africa/Maseru,29°18'S,27°30'E
Masqat,Oman,Asia/Muscat,23°37'N,58°36'E
Mbabane,Swaziland,Africa/Mbabane,26°18'S,31°06'E
Mecca,Saudi Arabia,Asia/Riyadh,21°26'N,39°49'E
Medina,Saudi Arabia,Asia/Riyadh,24°28'N,39°36'E
Melbourne,Australia,Australia/Melbourne,37°48'S,144°57'E
Mexico,Mexico,America/Mexico_City,19°20'N,99°10'W
Minsk,Belarus,Europe/Minsk,53°52'N,27°30'E
Mogadishu,Somalia,Africa/Mogadishu,02°02'N,45°25'E
Monaco,Priciplality Of Monaco,Europe/Monaco,43°43'N,7°25'E
Monrovia,Liberia,Africa/Monrovia,06°18'N,10°47'W
Montevideo,Uruguay,America/Montevideo,34°50'S,56°11'W
Moroni,Comoros,Indian/Comoro,11°40'S,43°16'E
Moscow,Russian Federation,Europe/Moscow,55°45'N,37°35'E
Moskva,Russian Federation,Europe/Moscow,55°45'N,37°35'E
Mumbai,India,Asia/Kolkata,18°58'N,72°49'E
Muscat,Oman,Asia/Muscat,23°37'N,58°32'E
N'Djamena,Chad,Africa/Ndjamena,12°10'N,14°59'E
Nairobi,Kenya,Africa/Nairobi,01°17'S,36°48'E
Nassau,Bahamas,America/Nassau,25°05'N,77°20'W
Naypyidaw,Myanmar,Asia/Rangoon,19°45'N,96°6'E
New Delhi,India,Asia/Kolkata,28°37'N,77°13'E
Ngerulmud,Palau,Pacific/Palau,7°30'N,134°37'E
Niamey,Niger,Africa/Niamey,13°27'N,02°06'E
Nicosia,Cyprus,Asia/Nicosia,35°10'N,33°25'E
Nouakchott,Mauritania,Africa/Nouakchott,20°10'S,57°30'E
Noumea,New Caledonia,Pacific/Noumea,22°17'S,166°30'E
Nuku'alofa,Tonga,Pacific/Tongatapu,21°10'S,174°00'W
Nuuk,Greenland,America/Godthab,64°10'N,51°35'W
Oranjestad,Aruba,America/Aruba,12°32'N,70°02'W
Oslo,Norway,Europe/Oslo,59°55'N,10°45'E
Ottawa,Canada,US/Eastern,45°27'N,75°42'W
Ouagadougou,Burkina Faso,Africa/Ouagadougou,12°15'N,01°30'W
P'yongyang,Democratic People's Republic of Korea,Asia/Pyongyang,39°09'N,125°30'E
Pago Pago,American Samoa,Pacific/Pago_Pago,14°16'S,170°43'W
Palikir,Micronesia,Pacific/Ponape,06°55'N,158°09'E
Panama,Panama,America/Panama,09°00'N,79°25'W
Papeete,French Polynesia,Pacific/Tahiti,17°32'S,149°34'W
Paramaribo,Suriname,America/Paramaribo,05°50'N,55°10'W
Paris,France,Europe/Paris,48°50'N,02°20'E
Perth,Australia,Australia/Perth,31°56'S,115°50'E
Phnom Penh,Cambodia,Asia/Phnom_Penh,11°33'N,104°55'E
Podgorica,Montenegro,Europe/Podgorica,42°28'N,19°16'E
Port Louis,Mauritius,Indian/Mauritius,20°9'S,57°30'E
Port Moresby,Papua New Guinea,Pacific/Port_Moresby,09°24'S,147°08'E
Port-Vila,Vanuatu,Pacific/Efate,17°45'S,168°18'E
Port-au-Prince,Haiti,America/Port-au-Prince,18°40'N,72°20'W
Port of Spain,Trinidad and Tobago,America/Port_of_Spain,10°40'N,61°31'W
Porto-Novo,Benin,Africa/Porto-Novo,06°23'N,02°42'E
Prague,Czech Republic,Europe/Prague,50°05'N,14°22'E
Praia,Cape Verde,Atlantic/Cape_Verde,15°02'N,23°34'W
Pretoria,South Africa,Africa/Johannesburg,25°44'S,28°12'E
Pristina,Albania,Europe/Tirane,42°40'N,21°10'E
Quito,Ecuador,America/Guayaquil,00°15'S,78°35'W
Rabat,Morocco,Africa/Casablanca,34°1'N,6°50'W
Reykjavik,Iceland,Atlantic/Reykjavik,64°10'N,21°57'W
Riga,Latvia,Europe/Riga,56°53'N,24°08'E
Riyadh,Saudi Arabia,Asia/Riyadh,24°41'N,46°42'E
Road Town,British Virgin Islands,America/Virgin,18°27'N,64°37'W
Rome,Italy,Europe/Rome,41°54'N,12°29'E
Roseau,Dominica,America/Dominica,15°20'N,61°24'W
Saint Helier,Jersey,Etc/GMT,49°11'N,2°6'W
Saint Pierre,Saint Pierre and Miquelon,America/Miquelon,46°46'N,56°12'W
Saipan,Northern Mariana Islands,Pacific/Saipan,15°12'N,145°45'E
Sana,Yemen,Asia/Aden,15°20'N,44°12'W
Sana'a,Yemen,Asia/Aden,15°20'N,44°12'W
San Jose,Costa Rica,America/Costa_Rica,09°55'N,84°02'W
San Juan,Puerto Rico,America/Puerto_Rico,18°28'N,66°07'W
San Marino,San Marino,Europe/San_Marino,43°55'N,12°30'E
San Salvador,El Salvador,America/El_Salvador,13°40'N,89°10'W
Santiago,Chile,America/Santiago,33°24'S,70°40'W
Santo Domingo,Dominica Republic,America/Santo_Domingo,18°30'N,69°59'W
Sao Tome,Sao Tome and Principe,Africa/Sao_Tome,00°10'N,06°39'E
Sarajevo,Bosnia and Herzegovina,Europe/Sarajevo,43°52'N,18°26'E
Seoul,Republic of Korea,Asia/Seoul,37°31'N,126°58'E
Singapore,Republic of Singapore,Asia/Singapore,1°18'N,103°48'E
Skopje,The Former Yugoslav Republic of Macedonia,Europe/Skopje,42°01'N,21°26'E
Sofia,Bulgaria,Europe/Sofia,42°45'N,23°20'E
Sri Jayawardenapura Kotte,Sri Lanka,Asia/Colombo,6°54'N,79°53'E
St. George's,Grenada,America/Grenada,32°22'N,64°40'W
St. John's,Antigua and Barbuda,America/Antigua,17°7'N,61°51'W
St. Peter Port,Guernsey,Europe/Guernsey,49°26'N,02°33'W
Stanley,Falkland Islands,Atlantic/Stanley,51°40'S,59°51'W
Stockholm,Sweden,Europe/Stockholm,59°20'N,18°05'E
Sucre,Bolivia,America/La_Paz,16°20'S,68°10'W
Suva,Fiji,Pacific/Fiji,18°06'S,178°30'E
Sydney,Australia,Australia/Sydney,33°53'S,151°13'E
Taipei,Republic of China (Taiwan),Asia/Taipei,25°02'N,121°38'E
T'bilisi,Georgia,Asia/Tbilisi,41°43'N,44°50'E
Tbilisi,Georgia,Asia/Tbilisi,41°43'N,44°50'E
Tallinn,Estonia,Europe/Tallinn,59°22'N,24°48'E
Tarawa,Kiribati,Pacific/Tarawa,01°30'N,173°00'E
Tashkent,Uzbekistan,Asia/Tashkent,41°20'N,69°10'E
Tegucigalpa,Honduras,America/Tegucigalpa,14°05'N,87°14'W
Tehran,Iran,Asia/Tehran,35°44'N,51°30'E
Thimphu,Bhutan,Asia/Thimphu,27°31'N,89°45'E
Tirana,Albania,Europe/Tirane,41°18'N,19°49'E
Tirane,Albania,Europe/Tirane,41°18'N,19°49'E
Torshavn,Faroe Islands,Atlantic/Faroe,62°05'N,06°56'W
Tokyo,Japan,Asia/Tokyo,35°41'N,139°41'E
Tripoli,Libyan Arab Jamahiriya,Africa/Tripoli,32°49'N,13°07'E
Tunis,Tunisia,Africa/Tunis,36°50'N,10°11'E
Ulan Bator,Mongolia,Asia/Ulaanbaatar,47°55'N,106°55'E
Ulaanbaatar,Mongolia,Asia/Ulaanbaatar,47°55'N,106°55'E
Vaduz,Liechtenstein,Europe/Vaduz,47°08'N,09°31'E
Valletta,Malta,Europe/Malta,35°54'N,14°31'E
Vienna,Austria,Europe/Vienna,48°12'N,16°22'E
Vientiane,Lao People's Democratic Republic,Asia/Vientiane,17°58'N,102°36'E
Vilnius,Lithuania,Europe/Vilnius,54°38'N,25°19'E
W. Indies,Antigua and Barbuda,America/Antigua,17°20'N,61°48'W
Warsaw,Poland,Europe/Warsaw,52°13'N,21°00'E
Washington DC,USA,US/Eastern,39°91'N,77°02'W
Wellington,New Zealand,Pacific/Auckland,41°19'S,174°46'E
Willemstad,Netherlands Antilles,America/Curacao,12°05'N,69°00'W
Windhoek,Namibia,Africa/Windhoek,22°35'S,17°04'E
Yamoussoukro,Cote d'Ivoire,Africa/Abidjan,06°49'N,05°17'W
Yangon,Myanmar,Asia/Rangoon,16°45'N,96°20'E
Yaounde,Cameroon,Africa/Douala,03°50'N,11°35'E
Yaren,Nauru,Pacific/Nauru,0°32'S,166°55'E
Yerevan,Armenia,Asia/Yerevan,40°10'N,44°31'E
Zagreb,Croatia,Europe/Zagreb,45°50'N,15°58'E

# UK Cities
Aberdeen,Scotland,Europe/London,57°08'N,02°06'W
Birmingham,England,Europe/London,52°30'N,01°50'W
Bolton,England,Europe/London,53°35'N,02°15'W
Bradford,England,Europe/London,53°47'N,01°45'W
Bristol,England,Europe/London,51°28'N,02°35'W
Cardiff,Wales,Europe/London,51°29'N,03°13'W
Crawley,England,Europe/London,51°8'N,00°10'W
Edinburgh,Scotland,Europe/London,55°57'N,03°13'W
Glasgow,Scotland,Europe/London,55°50'N,04°15'W
Greenwich,England,Europe/London,51°28'N,00°00'W
Leeds,England,Europe/London,53°48'N,01°35'W
Leicester,England,Europe/London,52°38'N,01°08'W
Liverpool,England,Europe/London,53°25'N,03°00'W
Manchester,England,Europe/London,53°30'N,02°15'W
Newcastle Upon Tyne,England,Europe/London,54°59'N,01°36'W
Newcastle,England,Europe/London,54°59'N,01°36'W
Norwich,England,Europe/London,52°38'N,01°18'E
Oxford,England,Europe/London,51°45'N,01°15'W
Plymouth,England,Europe/London,50°25'N,04°15'W
Portsmouth,England,Europe/London,50°48'N,01°05'W
Reading,England,Europe/London,51°27'N,0°58'W
Sheffield,England,Europe/London,53°23'N,01°28'W
Southampton,England,Europe/London,50°55'N,01°25'W
Swansea,England,Europe/London,51°37'N,03°57'W
Swindon,England,Europe/London,51°34'N,01°47'W
Wolverhampton,England,Europe/London,52°35'N,2°08'W
Barrow-In-Furness,England,Europe/London,54°06'N,3°13'W

# US State Capitals
Montgomery,USA,US/Central,32°21'N,86°16'W
Juneau,USA,US/Alaska,58°23'N,134°11'W
Phoenix,USA,America/Phoenix,33°26'N,112°04'W
Little Rock,USA,US/Central,34°44'N,92°19'W
Sacramento,USA,US/Pacific,38°33'N,121°28'W
Denver,USA,US/Mountain,39°44'N,104°59'W
Hartford,USA,US/Eastern,41°45'N,72°41'W
Dover,USA,US/Eastern,39°09'N,75°31'W
Tallahassee,USA,US/Eastern,30°27'N,84°16'W
Atlanta,USA,US/Eastern,33°45'N,84°23'W
Honolulu,USA,US/Hawaii,21°18'N,157°49'W
Boise,USA,US/Mountain,43°36'N,116°12'W
Springfield,USA,US/Central,39°47'N,89°39'W
Indianapolis,USA,US/Eastern,39°46'N,86°9'W
Des Moines,USA,US/Central,41°35'N,93°37'W
Topeka,USA,US/Central,39°03'N,95°41'W
Frankfort,USA,US/Eastern,38°11'N,84°51'W
Baton Rouge,USA,US/Central,30°27'N,91°8'W
Augusta,USA,US/Eastern,44°18'N,69°46'W
Annapolis,USA,US/Eastern,38°58'N,76°30'W
Boston,USA,US/Eastern,42°21'N,71°03'W
Lansing,USA,US/Eastern,42°44'N,84°32'W
Saint Paul,USA,US/Central,44°56'N,93°05'W
Jackson,USA,US/Central,32°17'N,90°11'W
Jefferson City,USA,US/Central,38°34'N,92°10'W
Helena,USA,US/Mountain,46°35'N,112°1'W
Lincoln,USA,US/Central,40°48'N,96°40'W
Carson City,USA,US/Pacific,39°9'N,119°45'W
Concord,USA,US/Eastern,43°12'N,71°32'W
Trenton,USA,US/Eastern,40°13'N,74°45'W
Santa Fe,USA,US/Mountain,35°40'N,105°57'W
Albany,USA,US/Eastern,42°39'N,73°46'W
Raleigh,USA,US/Eastern,35°49'N,78°38'W
Bismarck,USA,US/Central,46°48'N,100°46'W
Columbus,USA,US/Eastern,39°59'N,82°59'W
Oklahoma City,USA,US/Central,35°28'N,97°32'W
Salem,USA,US/Pacific,44°55'N,123°1'W
Harrisburg,USA,US/Eastern,40°16'N,76°52'W
Providence,USA,US/Eastern,41°49'N,71°25'W
Columbia,USA,US/Eastern,34°00'N,81°02'W
Pierre,USA,US/Central,44°22'N,100°20'W
Nashville,USA,US/Central,36°10'N,86°47'W
Austin,USA,US/Central,30°16'N,97°45'W
Salt Lake City,USA,US/Mountain,40°45'N,111°53'W
Montpelier,USA,US/Eastern,44°15'N,72°34'W
Richmond,USA,US/Eastern,37°32'N,77°25'W
Olympia,USA,US/Pacific,47°2'N,122°53'W
Charleston,USA,US/Eastern,38°20'N,81°38'W
Madison,USA,US/Central,43°4'N,89°24'W
Cheyenne,USA,US/Mountain,41°8'N,104°48'W

# Major US Cities
Birmingham,USA,US/Central,33°39'N,86°48'W
Anchorage,USA,US/Alaska,61°13'N,149°53'W
Los Angeles,USA,US/Pacific,34°03'N,118°15'W
San Francisco,USA,US/Pacific,37°46'N,122°25'W
Bridgeport,USA,US/Eastern,41°11'N,73°11'W
Wilmington,USA,US/Eastern,39°44'N,75°32'W
Jacksonville,USA,US/Eastern,30°19'N,81°39'W
Miami,USA,US/Eastern,26°8'N,80°12'W
Chicago,USA,US/Central,41°50'N,87°41'W
Wichita,USA,US/Central,37°41'N,97°20'W
Louisville,USA,US/Eastern,38°15'N,85°45'W
New Orleans,USA,US/Central,29°57'N,90°4'W
Portland,USA,US/Eastern,43°39'N,70°16'W
Baltimore,USA,US/Eastern,39°17'N,76°37'W
Detroit,USA,US/Eastern,42°19'N,83°2'W
Minneapolis,USA,US/Central,44°58'N,93°15'W
Kansas City,USA,US/Central,39°06'N,94°35'W
Billings,USA,US/Mountain,45°47'N,108°32'W
Omaha,USA,US/Central,41°15'N,96°0'W
Las Vegas,USA,US/Pacific,36°10'N,115°08'W
Manchester,USA,US/Eastern,42°59'N,71°27'W
Newark,USA,US/Eastern,40°44'N,74°11'W
Albuquerque,USA,US/Mountain,35°06'N,106°36'W
New York,USA,US/Eastern,40°43'N,74°0'W
Charlotte,USA,US/Eastern,35°13'N,80°50'W
Fargo,USA,US/Central,46°52'N,96°47'W
Cleveland,USA,US/Eastern,41°28'N,81°40'W
Philadelphia,USA,US/Eastern,39°57'N,75°10'W
Sioux Falls,USA,US/Central,43°32'N,96°43'W
Memphis,USA,US/Central,35°07'N,89°58'W
Houston,USA,US/Central,29°45'N,95°22'W
Dallas,USA,US/Central,32°47'N,96°48'W
Burlington,USA,US/Eastern,44°28'N,73°9'W
Virginia Beach,USA,US/Eastern,36°50'N,76°05'W
Seattle,USA,US/Pacific,47°36'N,122°19'W
Milwaukee,USA,US/Central,43°03'N,87°57'W
San Diego,USA,US/Pacific,32°42'N,117°09'W
Orlando,USA,US/Eastern,28°32'N,81°22'W
Buffalo,USA,US/Eastern,42°54'N,78°50'W
Toledo,USA,US/Eastern,41°39'N,83°34'W

# Canadian cities
Vancouver,Canada,America/Vancouver,49°15'N,123°6'W
Calgary,Canada,America/Edmonton,51°2'N,114°3'W
Edmonton,Canada,America/Edmonton,53°32'N,113°29'W
Saskatoon,Canada,America/Regina,52°8'N,106°40'W
Regina,Canada,America/Regina,50°27'N,104°36'W
Winnipeg,Canada,America/Winnipeg,49°53'N,97°8'W
Toronto,Canada,America/Toronto,43°39'N,79°22'W
Montreal,Canada,America/Montreal,45°30'N,73°33'W
Quebec,Canada,America/Toronto,46°48'N,71°14'W
Fredericton,Canada,America/Halifax,45°57'N,66°38'W
Halifax,Canada,America/Halifax,44°38'N,63°34'W
Charlottetown,Canada,America/Halifax,46°14'N,63°7'W
St. John's,Canada,America/Halifax,47°33'N,52°42'W
Whitehorse,Canada,America/Whitehorse,60°43'N,135°3'W
Yellowknife,Canada,America/Yellowknife,62°27'N,114°22'W
Iqaluit,Canada,America/Iqaluit,63°44'N,68°31'W
"""
# endregion

GroupName = str
GroupInfo = Dict
LocationInfoList = List[LocationInfo]
LocationDatabase = Dict[GroupName, GroupInfo[str, LocationInfoList]]


def database() -> LocationDatabase:
    """Returns a database populated with the inital set of locations stored
    in this module
    """
    db: LocationDatabase = {}
    _add_locations_from_str(_LOCATION_INFO, db)
    return db


def _sanitize_key(key) -> str:
    """Sanitize the location or group key to look up

    Args:
        key: The key to sanitize
    """
    return str(key).lower().replace(" ", "_")


def _location_count(db: LocationDatabase) -> int:
    """Returns the count of the locations currently in the database"""
    return reduce(lambda count, group: count + len(group), db.values(), 0)


def _get_group(name: str, db: LocationDatabase) -> Optional[GroupInfo]:
    return db.get(name, None)


def _add_location_to_db(location: LocationInfo, db: LocationDatabase) -> None:
    """Add a single location to a database"""
    key = _sanitize_key(location.timezone_group)
    group = _get_group(key, db)
    if not group:
        group = {}
        db[key] = group

    location_key = _sanitize_key(location.name)
    if location_key not in group:
        group[location_key] = [location]
    else:
        group[location_key].append(location)


def _indexable_to_locationinfo(idxable) -> LocationInfo:
    return LocationInfo(
        name=idxable[0],
        region=idxable[1],
        timezone=idxable[2],
        latitude=dms_to_float(idxable[3], 90.0),
        longitude=dms_to_float(idxable[4], 180.0),
    )


def _add_locations_from_str(location_string: str, db: LocationDatabase) -> None:
    """Add locations from a string."""

    for line in location_string.split("\n"):
        line = line.strip()
        if line != "" and line[0] != "#":
            info = line.split(",")
            location = _indexable_to_locationinfo(info)
            _add_location_to_db(location, db)


def _add_locations_from_list(
    location_list: List[Union[Tuple, str]], db: LocationDatabase
) -> None:
    """Add locations from a list of either strings or lists of strings or tuples of strings."""
    for info in location_list:
        if isinstance(info, str):
            _add_locations_from_str(info, db)
        elif isinstance(info, (list, tuple)):
            location = _indexable_to_locationinfo(info)
            _add_location_to_db(location, db)


def add_locations(locations: Union[List, str], db: LocationDatabase) -> None:
    """Add locations to the database.

    Locations can be added by passing either a string with one line per location or by passing
    a list containing strings, lists or tuples (lists and tuples are passed directly to the
    LocationInfo constructor)."""
    if isinstance(locations, str):
        _add_locations_from_str(locations, db)
    elif isinstance(locations, (list, tuple)):
        _add_locations_from_list(locations, db)


def group(region: str, db: LocationDatabase) -> GroupInfo:
    """Access to each timezone group. For example London is in timezone
    group Europe.

    Lookups are case insensitive

    Args:
        region: the name to look up

    Raises:
        KeyError: if the location is not found
    """
    key = _sanitize_key(region)
    for name, value in db.items():
        if name == key:
            return value

    raise KeyError(f"Unrecognised Group - {region}")


def lookup_in_group(location: str, group: Dict) -> LocationInfo:
    """Looks up the location within a group dictionary

    You can supply an optional region name by adding a comma
    followed by the region name. Where multiple locations have the
    same name you may need to supply the region name otherwise
    the first result will be returned which may not be the one
    you're looking for::

        location = group['Abu Dhabi,United Arab Emirates']

    Lookups are case insensitive.

    Args:
        location: The location to look up
        group: The location group to look in

    Raises:
        KeyError: if the location is not found
    """
    key = _sanitize_key(location)

    try:
        lookup_name, lookup_region = key.split(",", 1)
    except ValueError:
        lookup_name = key
        lookup_region = ""

    lookup_name = lookup_name.strip("\"'")
    lookup_region = lookup_region.strip("\"'")

    for (location_name, location_list) in group.items():
        if location_name == lookup_name:
            if lookup_region == "":
                return location_list[0]

            for loc in location_list:
                if _sanitize_key(loc.region) == lookup_region:
                    return loc

    raise KeyError(f"Unrecognised location name - {key}")


def lookup(name: str, db: LocationDatabase) -> Union[Dict, LocationInfo]:
    """Look up a name in a database.

    If a group with the name specified is a group name then that will
    be returned. If no group is found a location with the name will be
    looked up.

    Args:
        name: The group/location name to look up
        db:   The location database to look in

    Raises:
        KeyError: if the name is not found
    """

    key = _sanitize_key(name)
    for group_key, group in db.items():
        if group_key == key:
            return group

        try:
            return lookup_in_group(name, group)
        except KeyError:
            pass

    raise KeyError(f"Unrecognised name - {name}")


def all_locations(db: LocationDatabase) -> Generator[LocationInfo, None, None]:
    """A generator that returns all the :class:`~astral.LocationInfo`\\s contained in the database
    """
    for group_info in db.values():
        for location_list in group_info.values():
            for location in location_list:
                yield location
