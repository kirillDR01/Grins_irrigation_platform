# Excel Data Migration Report — Railway Dev

**Committed**: 2026-04-16 ~07:35 UTC  
**Script**: `scripts/import_excel_data.py`  
**Target**: Railway Dev (Postgres-PH_d @ shortline.proxy.rlwy.net:47551)  
**Errors**: 0 across all 4 phases  
**Source Files**:
- `Viktor_excel/migration/Final.xlsx` (330 data rows)
- `Viktor_excel/migration/Lead Tracking List .xlsx` (22 data rows, sheet "Sales List")

---

## Table Count Changes

| Table | Before | After | Delta |
|---|---|---|---|
| **customers** | 110 | 350 | **+240** |
| **leads** | 52 | 62 | **+10** |
| **jobs** | 252 | 552 | **+300** |
| **properties** | 106 | 424 | **+318** |
| **sales_entries** | 0 | 22 | **+22** |
| **service_agreements** | 111 | 111 | 0 (unchanged) |

---

## Phase 1: Final.xlsx -> Customers + Properties + Jobs

**Input**: 330 rows from Final.xlsx (Sheet1)

| Metric | Count |
|---|---|
| Existing customers matched | 107 |
| Leads converted to customers | 15 |
| New customers created | 204 |
| Properties created | 297 |
| Properties reused (existing) | 27 |
| Jobs created | 300 |
| Jobs skipped (duplicate) | 26 |
| TBD jobs (needs mass outreach) | 106 |
| Svc Pkg flagged (no agreement) | 1 |
| Rows skipped (no phone) | 0 |
| Rows skipped (bad phone) | 4 |
| Errors | 0 |

**Totals check**: 107 existing + 15 converted + 204 new + 4 skipped = 330 rows.

---

### 15 Leads Converted to Customers

These people existed in the leads table and were promoted to full customers with their lead marked `status = 'converted'`.

| Name | Lead Name in DB | New Customer ID |
|---|---|---|
| Alec Bunting | Alec Bunting | 8b764f53-51bb-4a6d-8197-31899e0633e9 |
| Anand Kalathil | Anand Kalathil | 9ac785f0-a052-4556-a8d9-e469a11a1bf4 |
| Brandon Walter | Brandon Walter | 2bd1d7f7-c913-4db8-8684-7a77390976e6 |
| Elaine Kilby | Elaine Kilby | 57da3beb-e628-4286-87cf-2c6ad3ff2586 |
| Geneva Fender | Geneva Fender | 37752b19-5e48-486e-85ae-0e9e4a779bd9 |
| Jim Sinning | Jim Sinning | ac1520e6-a81c-448b-b558-5ce9bc046bd9 |
| Lee Olson | LEE OLSON | fb40cd38-32ef-4c26-955a-66422cc50ff3 |
| Matt Lilja | Matt Lilja | 63bcf3e3-269c-4fd9-a970-34bcf02f95b0 |
| Max Barsky | Max Barsky | faed902a-492c-4814-8e86-4bbacb13a1af |
| Mike Romashin | Mike Romashin | 5dbeb071-e778-45fe-b38b-f14e509c585d |
| Natalie Simons | Natalie Simons | f2098c80-1f6e-4037-a46e-7d359b64725f |
| Hyunsook Kim | Hyunsook Kim | 28e0a4f0-7ce8-48cd-a5c3-9fb4cd628bfa |
| Martin cook | Martin Cook | 01f2963c-f756-4297-a852-98abe9cfeb27 |
| Ramon Pastrano | Ramon Pastrano | 1b51c6db-7f4e-4599-b11f-bac247063c24 |
| Vitalie mosneguta | Vitalie mosneguta | 063cd754-9829-49ae-aec4-e0542fab0f71 |

---

### 204 New Customers Created

| Name | Phone | City | Email |
|---|---|---|---|
| Yashodhan Dhore | 6123106180 | Plymouth | yashdhore@gmail.com |
| Aaron Reiter | 6126698893 | Eden prairie, mn | Reiter.aaron@gmail.com |
| Abdelwahaab Akef | 6127471151 | Plymouth | asakef@hotmail.com |
| Adi Andrew-Jaja | 7632329626 | Champlin | Adiaj63@gmail.com |
| Adil Elamri | 6122987592 | Minnetonka | Omardrees@gmnail.com |
| Aldris | 6128654100 | Tonka Bay | NEED TO COLLECT |
| Aleksey Derevyanko | 9524575394 | Edina | naissurmk2@gmail.com |
| Alena Paley | 7636706995 | Plymouth | olenarealty@yahoo.com |
| Alex Tkatch Building | 7632831775 | Coon Rapids | Alext@abcexteriorsmn.com |
| Alexander Fadeyev | 9522977477 | Savage | alex_init@hotmail.com |
| Alexander Kartaev | 6129875987 | Plymouth | kartayeu@gmail.com |
| Alisa Richardson | 6123236616 | Minnetonka | richardson.alisa@gmail.com |
| Allan Callander | 9522391497 | Minnetonka | atc78628@live.com |
| Amy Redlon | 6123256605 | Chaska | amyredlon@gmail.com |
| And and Doug Cusack | 6083479143 | Bloomington | abcdcusack@gmail.com |
| Andrew Damyan Savage | 6126850277 | Savage | Mbqc4best@yahoo.com |
| Andrew Droen | 7635160541 | Rogers | akdroen@gmail.com |
| Andrew Fisher | 7639130159 | Plymouth MN. | As-bafisher@msn.com |
| Angi | 6122753001 | Minneapolis | NEED TO COLLECT |
| Anjali Srivastava | 6127508497 | Plymouth | rv0655@gmail.com |
| Ari Dalal | 3476036795 | Plymouth | arihantdalal@gmail.com |
| Arpad | 6129866240 | Edina | Anagy@mgmbloomington.com |
| Arthur lee | 6127510982 | Plymouth | NEED TO COLLECT |
| Ash Jafri | 2695993311 | Maple Grove | jafri.ash@gmail.com |
| Ashish Srivastava | 6516002484 | Eden Prairie | ashish214a@gmail.com |
| Ateeq ur Rahman | 6129101825 | Minneapolis | ateeq.rahman@gmail.com |
| Ben Fanning | 6123062203 | bfann21@gmail.com | bfann21@gmail.com |
| Bhaskar Archarya | 9522105365 | Eden Praire | abhaskar@hotmail.com |
| Bon (EP) | 6783142822 | Eden Prairie | TBD |
| Boris Parker | 6125908345 | Wayzata and Hopkins | Boris@parkerlawus.com |
| Brent J. Ryan | 7634588674 | Plymouth | NEED TO COLLECT |
| Brett Reinhart | 9527381178 | Plymouth | brettjreinhart@gmail.com |
| Brian Marrin | 2146322381 | Maple grove | Brian.marrin@outlook.com |
| Brian Martin | 7637100202 | Brooklyn Park | blackfalcon1210@gmail.com |
| Brian Pergament | 6514857970 | St. Louis Park | brian@pergolaonline.com |
| Brian Wasserman | 6125781325 | Plymouth | brian.wasserman@cbre.com |
| Bruce VanderSchaaf | 6128104257 | Maple Grove | Bruce.vanderschaaf@outlook.com |
| Caroline Cauley | 3362027674 | Eden Prairie | cauleycp@gmail.com |
| Chad Overskei | 6122193589 | Maple Grove | skei13@hotmail.com |
| Chetan Shenoy | 7322214061 | Plymouth | cshenoy3@gmail.com |
| Christine Wiechmann | 7637727892 | Saint Michael | Cwiechmann12@gmail.com |
| Chris Narins | 6129658675 | Eden Prairie | cvnarins@gmail.com |
| Cityline Homes | 7634431032 | Chanhassen | borodin79@gmail.com |
| Dan Vartolomei | 7633521458 | Medina | dannvartolomei@gmail.com |
| Dave Asinger | 6125087372 | Maple Grove | Dave.Asinger@MidwestRadiology.com |
| David Gustafson | 7632214001 | Plymouth | selectmarketing@msn.com |
| Dave Olson | 6512952712 | Edina | david@supercrewcontractors.com |
| David Smith | 6123452936 | Eden Prairie | Davsmico@yahoo.com |
| Dennis Shumkov | 9526498058 | Plymouth | denchik.shumkov@gmail.com |
| Diane | 6127090965 | Savage | msdispom@gmail.com |
| Dmitri Shtulman | 6127039786 | Plymouth | dshtulman@hotmail.com |
| Duane randall | 6127019994 | Medina | Xcrandallx@yahoo.com |
| Elizabeth Johnson | 6129655631 | Richfield | esinarath@yahoo.com |
| Ellen MacRae | 9496780226 | Prior Lake | 1ellenmacrae@gmail.com |
| Eric Ernst | 6129642085 | Edina | eernst@umphysicians.Umn.edu |
| Felix (Client) | 5076157524 | Plymouth | felix@rocknmulchlandscaping.com |
| Francine Hartig | 6122909230 | Medina | TBD |
| Freeborn Emadamerho | 6122426279 | Dayton | Raybon7553@gmail.com |
| Fritz | 6127511100 | Tonka Bay | Start Up & Irrigation Install |
| Garret C. | 6023867098 | Edina | garret.cerkvenik@gmail.com |
| Gary Bischel | 6512025621 | orono | Kebischel@gmail.com |
| Gina | 4149756909 | Maple Grove | gmt0215@yahoo.com |
| Ginger Anzalone | 2813842827 | Medina | Gingeranzalone12@gmail.com |
| Giordani crawforf | 7634385099 | Eden Prairie | giordanicc@gmail.com |
| Helena Lekah | 9525002512 | Apple Valley | Hlekah@gmail.com |
| Helenbeth reynolds | 6124187931 | Medina | Helenbethreynoldsmph@me.com |
| Igor Lelchuk | 9522399421 | Victoria | lely09@yahoo.com |
| Isabella Nocera | 8455006835 | Osseo | ignocera@yahoo.com |
| Ismael Martinez | 6128670678 | Deephaven | ismaelmartinezortiz@gmail.com |
| Jackie Sperling Hosseini | 4148015502 | Eden Prairie | jacquelinebeth1987@gmail.com |
| James C. Blosser | 7632212329 | Maple Grove | jamesblosser@gmail.com |
| Jim Damiani | 6122706318 | Plymouth | jim.damiani@nmrk.com |
| Jim Hanggi | 6129638183 | Bloomington | jimhanggi@hotmail.com |
| James Lenz | 6128492520 | Medina | jameslenzjr@gmail.com |
| Jim Matejcel | 6123090399 | Plymouth | jim@mfcorp.com |
| Jamie Kollen | 5073278337 | Plymouth | jamie.j.kollen@gmail.com |
| Jessica Kleine | 6122800208 | Medina | Jessica.l.kleine@gmail.com |
| Jill Reynolds | 6127181533 | Plymouth | Jillereynolds@icloud.com |
| Jocelyne Mei | 3175062379 | Maple Grove | Meijocelyne@gmail.com |
| John Jerabek | 6126957660 | Maple Grove | ajerabek4@msn.com |
| Jonathan Wolf | 7136283015 | Eden Prairie | jonathan_wolf@sbcglobal.net |
| Joseph Ndubisi | 6122024007 | Brooklyn Park | josephndubisi@gmail.com |
| Josh Baltzer | 9522701681 | Medina | josh.baltz009@gmail.com |
| Julian Johnson | 6124378803 | Plymouth | juliancjohnson@live.com |
| Julie Dmitrev | 6128689212 | Plymouth | juliedmitrev@gmail.com |
| Katherine | 6126161980 | Edina | kkbrokerage@gmail.com |
| Katz Ilya | 6125326223 | Minnetonka | Isk321@comcast.net |
| Kerry Creeron | 6083454935 | Hopkins | kerrycr@gmail.com |
| Kim Levine | 4025414773 | Golden Valley | kimtendo@mac.com |
| Kim Senn | 4156068897 | Edina | kimberly.senn@gmail.com |
| Kirk Williams | 6125998884 | Plymouth | Kirk555@comcast.net |
| Kolosov | 6122024223 | Blaine | itkolosov@gmail.com |
| Kori Randle | 9523033131 | Eden Prairie | kwrandle@gmail.com |
| KP Patil | 6128651367 | Plymouth | kaustubh.r.patil@gmail.com |
| Kristi Hendriks | 7636883751 | Medina | TBD |
| Kristin Illingworth | 5132571778 | Hamel | kristin.illingworth@gmail.com |
| Kristin Kuderer | 9522212285 | 11071 Jackson Drive | kkuderer27@gmail.com |
| Kyle Loving | 9522007874 | Prior Lake | Kyle.loving27@gmail.com |
| Laura Benson | 6129787619 | Medina | Labenson99@gmail.com |
| Laura Collier | 6122375478 | Edina | laurasc8375@yahoo.com |
| Laura Dahlen | 6128670433 | Champlin | Ldahlen88@outlook.com |
| Laura Kotteman (INCLUDE HUSBAND IN TEXT) | 4107465977 | Wayzata | lsellinger@gmail.com / kraig.kottemann@gmail.com |
| Lee Dummer | 7635931098 | Crystal | L_dummer@hotmail.com |
| Loffler St. Louis Park | 9522926928 | St. Louis Park | Matt Email: matt.braaten@ajdagny.com |
| Lokendra Chauhan | 6124427956 | Eden Prairie | lokendra.chauhan@gmail.com |
| Lynda Tran | 7635684281 | Corcoran | ltran85@hotmail.com |
| Madalyn Larsen | 2624410662 | Eden prairie | wohlmad@gmail.com |
| MANIT SINGLA | 3127302950 | Edina | wsu397@gmail.com |
| Marian Schrah | 6127036518 | Plymouth | marian_schrah@msn.com |
| Martin Robinson | 7634788546 | Medina | gmdsrobertson@msn.com |
| Max Ryabinin | 6512388260 | Rosemount | kolobok88@yahoo.com |
| Melissa Lee | 6124015037 | Maple Grove | Mleejohnson1@yahoo.com |
| Mike | 6123860993 | Edina | Landscaping |
| Mike lecy- home health care inc | 9527976939 | Golden Valley | Mike.lecy@hhcare.net |
| Mike Leonard | 6127231369 | Plymouth | Mike2510@comcast.net |
| Mike Reier | 7632423042 | Plymouth | Mreier@comcast.net |
| Michael Tobak | 6128032020 | Wayzata | Mishamnusa@gmail.com |
| Mohamed Remtula | 6127150034 | Maple Grove | Mremtula@comcast.net |
| Mohammed Solaiman | 5073800393 | 4355 Vinewood Ln N, Plymouth, MN 55442 | Solaiman.mohammed@mayo.edu |
| Molly King | 6126702516 | 12725 43rd Ave N | mollykathleen5@gmail.com |
| Muz Zaman | 9523346964 | Maple Grove | mz1984@gmail.com |
| Nadia Han | 6129861355 | Plymouth | jingfg5918@gmail.com |
| Natalie Smoliak | 6513358522 | Savage | nataliesmoliak@gmail.com |
| Nataliya Krupatkykh | 9522104939 | Maple Grove | Krupatkykh@yahoo.com |
| Nemat janetkhan | 9524513053 | Eden Prairie | Nemat@janetkhangroup.com |
| Nick Alms | 6124998683 | Plymouth | nalms@greinerconstruction.com |
| Nick Eisinger | 7632296211 | Medina | neisinger@comcast.net |
| Nina | 9529940280 | Eden Prairie | ninababa@yahoo.com |
| Nishant Jain | 6127032671 | Eden Prairie | nishant.c.jain@gmail.com |
| Ondrej Vesely | 6123088354 | Maple Grove | NEED TO COLLECT |
| Otto | 6128027291 | Long Lake | NEED TO COLLECT |
| Paul Brazel | 9528385676 | Maple Grove | pnbrazel@gmail.com |
| Paul Dickman | 6512695340 | Maple Grove | P.h.dickman@hotmail.com |
| Prasanth Prabhakaran | 9206348275 | Plymouth | prasanthorion@yahoo.co.in |
| Quint Rubald | 6129636699 | Medina | Qrubald@summitfire.com |
| Rachel Sanzone | 6512161365 | Plymouth | rlsanzo1123@gmail.com |
| Randy Anderson | 6128054906 | Plymouth | 69bbdartgts@gmail.com |
| Reese Pfeiffer | 7632428911 | Plymouth | Jeannepfeiffer@msn.com |
| Rick Duvall | 6128652195 | Plymouth | RICK.DUVALL55@GMAIL.COM |
| Richard Lu | 6128599565 | Medina | richard.lu@mchsi.com |
| Rita | 7633606634 | Plymouth | ritashifman@gmail.com |
| Roger Sims | 9702141137 | Eden Prairie | rogerdsims@gmail.com |
| Roman Keller | 3208280547 | Maple Grove | romankeller@gmail.com |
| Sai Prasad | 7638078650 | Maple Grove | sai1819@gmail.com |
| Serenity on the Greenway x2 | 8162135778 | Plymouth | Mnrwright3@gmail.com |
| Sergey Kenigsberg | 6123107739 | Plymouth | Serrgey@cityinsurancemn.com |
| Sergey Lelyukh | 9524512055 | Shakopee | TBD |
| Sharon Robarge | 7632135007 | Crystal | mordy66@gmail.com |
| Sheree Schattenmann | 7135303721 | Golden Valley | Shereephd@gmail.com |
| Sherry Rudi | 6126363340 | Medina | sherry_rudin@hotmail.com |
| Siva Tharmalingam | 9522103151 | Eden Prairie | Sivathar1977@gmail.com |
| Stepan Elm Creek HOA | 7635686679 | Maple Grove | stefan@qualitymowing.com |
| Steve Conley & Christine Conley | 3207663277 | Edina | Conley.Stevenj@gmail.com & cbhockey@gmail.com |
| Steven Cornfield | 2488604836 | Edina | Sod & Irrigation Install |
| Steven Magagna | 7344784896 | Minnetonka | stevenmagagna@gmail.com |
| Stephen Wilson | 6518954922 | Eden Prairie | wilsons2175@gmail.com |
| Suzanne Flottmeier | 6123826293 | Maple Grove | Sflottmeier@comcast.net |
| Swapnil Salunke | 6123068203 | Eden Prairie | swapnil.salunke@gmail.com |
| Thomas McNanley | 9522328737 | Medina | tmcna@mac.com |
| Tom Peterson | 9524124235 | Plymouth | mnpetersons@gmail.com |
| Timothy Wyatt | 2818252960 | Wayzata | Irrigation Install |
| Tracie Medina | 7633003743 | Chanhassen | tracie.reynolds4@gmail.com |
| Tracy Sellman | 9522107609 | Plymouth | tracysellman2004@yahoo.com |
| Trickey Helen | 9529335870 | Minnetonka | trickey4011@comcast.net |
| vadim oayenyagra | 6122278058 | Brooklyn Park | vadimoayenyagra@gmail.com |
| Val Quinn | 6123003799 | Eden Prairie | val.harnvarakiat@gmail.com |
| Venkatesh Rengasamy | 9522705175 | Eden Prarie | Venkatesh.rengasamy@gmail.com |
| Wayne Newton | 6128891065 | Eden Prairie | NEED TO COLLECT |
| Wild Meadows (x7) | 6127232816 | Medina | NEED TO COLLECT |
| Yan KUCHEROV | 7634582964 | Oak Grove MN 55011 | Yankucherov24@gmail.com |
| Yefim Tsukerman x2 | 7634432569 | Maple Grove | yefimts@yahoo,com |
| Zach Carpenter | 4142416055 | Chanhassen | zachcarp123@gmail.com |
| AJ Dagney | 6122207017 | Roseville | Matt Email: matt.braaten@ajdagny.com |
| Andres Caballero | 6517569816 | Maple Grove | act.msp@gmail.com |
| Charles Stuber | 6122392482 | Dayton | varmie1a@gmail.com |
| Dan Kuhlman | 6128501400 | Plymouth | dkuhlman@gmail.com |
| David Schmaltz | 6122019815 | Maple Grove | Dschmaltz@merchantgould.com |
| Dilip Desai | 9522505340 | Shakopee | dmdesai67@gmail.com |
| Djamil | 6123450165 | Excelsior | Djamil@partnersdentalstudio.com |
| Eric Ice | 9522003091 | Plymouth | eric.michael.ice@gmail.com |
| Golam Sayeed | 7632322026 | Plymouth | gsayeed@gmail.com |
| Igor Sovostyanov | 6124437070 | Plymouth | igorsovostanov@gmail.com |
| Irina Lefko | 7638986027 | Falcon Heights | Irina.lefko@gmail.com |
| Kairav Vakil | 3178503429 | 5808 View Ln Edina 55436 | kairavvakil@gmail.com |
| Kavitha Kamath | 9526882009 | Eden Prairie | kavith.kamath@gmail.com |
| Ken Mayer | 6127999823 | Otsego | kjmax0060@gmail.com |
| Kevin Ott | 7634648404 | Maple Grove | Kevdog23@icloud.com |
| Kevin Weirich | 6123237144 | Medina | weirichk@yahoo.com |
| Krista Engebretson | 6514705048 | Eden Prairie | krista.engebretson@gmail.com |
| Ksenia Ezekoye | 6517281467 | Eden Prairie | Ksenia.kowitz@gmail.com |
| Lauren LaHaye | 9524950867 | Hamel | Laurennlahaye@gmail.com |
| Matt Weidinger | 6125990790 | Maple Grove | Johnyutah53@gmail.com |
| Nabeel Ailabouni | 6514851039 | Maple Grove | nabeel.ailabouni@icloud.com |
| Natella (Fima) | 9529944744 | Minnetonka | TBD |
| Nicholas Brown | 6128501479 | Plymouth | farhillbrown@msn.com |
| Robin Pardue | 6124818250 | Maple Grove | robinpardue@mdn.com |
| Rustam Muharamov | 6124443333 | edina | rustammoore@gmail.com |
| Samantha Sonday | 2692035186 | Hopkins | slsonday67@gmail.com |
| Samuel Anim | 7634583589 | Brooklyn Park | Skanim69@gmail.com |
| Sarah Stang | 7637728717 | Edina | Sarahstang81@gmail.com |
| Steve Woodley (HOA) | 6125701030 | Bloomington | swoodley@sageviewadvisory.com |
| Taylor Pettis | 6124836509 | Minneapolis | Taylorpettis@gmail.com |
| Terri Schoenfelder | 7638075075 | Plymouth | Schoenfelder6@gmail.com |
| Wesley Yang | 8606300371 | Plymouth | wesleyyang1998@gmail.com |

---

### 106 TBD Customers Needing Mass Outreach

These customers had "TBD" or no specific week requested. Jobs were created as `to_be_scheduled` with null target dates. Each customer was flagged with `[MIGRATION] TBD scheduling - needs outreach` in their `internal_notes` field.

1. Abdelwahaab Akef
2. Adi Andrew-Jaja
3. Aldris
4. Alec Bunting
5. Aleksey Derevyanko
6. Alena Paley
7. Alexander Fadeyev
8. Allan Callander
9. Amy Redlon
10. And and Doug Cusack
11. Andrew Droen
12. Andrew Fisher
13. Angi
14. Anjali Srivastava
15. Ari Dalal
16. Arpad
17. Arthur lee
18. Ateeq ur Rahman
19. Bhaskar Archarya
20. Bon (EP)
21. Boris Parker
22. Brett Reinhart
23. Brian Marrin
24. Brian Martin
25. Brian Pergament
26. Brian Wasserman
27. Chad Overskei
28. Chris Narins
29. David Gustafson
30. Dennis Shumkov
31. Duane randall
32. Elaine Kilby
33. Eric Ernst
34. Eugene Borodin
35. Felix (Client)
36. Felix (Personal)
37. Francine Hartig
38. Freeborn Emadamerho
39. Gina
40. Ginger Anzalone
41. Helenbeth reynolds
42. Igor Lelchuk
43. James C. Blosser
44. James Lenz
45. Jill Reynolds
46. Jonathan Wolf
47. Josh Baltzer
48. Julian Johnson
49. Julie Dmitrev
50. Katherine
51. Kim Senn
52. Kirk Williams
53. Kolosov
54. KP Patil
55. Kristi Hendriks
56. Kyle Loving
57. Laura Collier
58. Laura Dahlen
59. Lee Dummer
60. Lynda Tran
61. Madalyn Larsen
62. MANIT SINGLA
63. Marian Schrah
64. Martin Robinson
65. Max Ryabinin
66. Mike Leonard
67. Mike Romashin
68. Mohamed Remtula
69. Nadia Han
70. Natalie Smoliak
71. Nathan Kelly Rice
72. Nemat janetkhan
73. Nick Alms
74. Nina
75. Ondrej Vesely
76. Paul Brazel
77. Prasanth Prabhakaran
78. Randy Anderson
79. Reese Pfeiffer
80. Rick Duvall
81. Richard Lu
82. Rita
83. Sai Prasad
84. Sergey Kenigsberg
85. Sergey Lelyukh
86. Sheree Schattenmann
87. Sherry Rudi
88. Siva Tharmalingam
89. Stephen Wilson
90. Suzanne Flottmeier
91. Swapnil Salunke
92. Tom Peterson
93. vadim oayenyagra
94. Venkatesh Rengasamy
95. Andres Caballero
96. Dan Kuhlman
97. David Schmaltz
98. Eric Ice
99. Golam Sayeed
100. Irina Lefko
101. Kevin Ott
102. Krista Engebretson
103. Nabeel Ailabouni
104. Natella (Fima)
105. Samuel Anim
106. Taylor Pettis

---

### 4 Rows Skipped (Malformed Phone Numbers)

| Row # | Name | Phone Value | Reason |
|---|---|---|---|
| 114 | Island home | (CALL RIGO) | Not a phone number |
| 131 | Jesse Huebsch | 95219133393 | 11 digits, does not start with 1 |
| 145 | Josh Franz | 6912-910-6551 | 11 digits after stripping, invalid |
| 246 | Samuel Goldfarb | 267-40805940 | 11 digits after stripping, invalid |

**Action required**: These 4 people need to be manually entered into the CRM with corrected phone numbers.

---

### 26 Jobs Skipped (Duplicate)

These were existing customers (107 matched) who already had an active job of the same type. No duplicate job was created.

---

### 1 Service Package Flag

One newly created customer was marked with `Service Package = Yes` in the Excel but had no existing service agreement in the database. Their `internal_notes` were updated with `[MIGRATION] Svc Pkg=Yes but no agreement - needs setup`.

---

## Phase 2: Lead Tracking List -> Sales Pipeline

**Input**: 22 rows from Lead Tracking List .xlsx (Sales List sheet)

| Metric | Count |
|---|---|
| Existing customers used | 1 |
| Existing leads updated | 11 |
| New leads created | 10 |
| New customers created | 21 |
| Properties created | 21 |
| Sales entries created | 22 |
| Rows skipped (no phone) | 0 |
| Errors | 0 |

### Row-by-Row Detail

| Name | Phone | Excel Job Type | DB Job Type | Excel Status | Pipeline Status | Action |
|---|---|---|---|---|---|---|
| Brandon Peterson | 9527697138 | Sod & Irrigation Install | new_installation | Pending Response | schedule_estimate | new_lead |
| Jason Skolak | 3035883856 | Irrigation Install | new_installation | Pending Response | schedule_estimate | new_lead |
| Maria Starchook-Moore | 6129900255 | Sod Install | installation | Pending House Offer... | schedule_estimate | new_lead |
| Paul Doppmann | 6128490140 | Irrigation Install | new_installation | Pending Response | schedule_estimate | new_lead |
| Brooke Jore | 7632917443 | Irrigation Install | new_installation | Pending Response | schedule_estimate | new_lead |
| Roman Keller | 3208280547 | Sod Install | installation | Pending Response | schedule_estimate | existing_customer |
| Charles Shelton | 7635017635 | Sod & Irrigation Install | new_installation | Pending Response | schedule_estimate | new_lead |
| Jim Sterner | 6122092961 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Derrick Washington | 6127033950 | Irrigation Install | new_installation | WAITING FOR CLOSING ON MAY 1st... | schedule_estimate | existing_lead |
| Patricia Bruns | 7632136391 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Tricia Braun | 6512701106 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Jeremy Brandt | 9529941946 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Greg Alexander | 6514919442 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Ken Lawrence | 6129161173 | Irrigation Install | new_installation | Pending Response | schedule_estimate | existing_lead |
| Dorthy Croskey | 6125186469 | Irrigation Refurbish | repair | Scheduled | estimate_scheduled | new_lead |
| Mary Didbold | 6123600205 | Irrigation & landscaping | installation | Pending Response | schedule_estimate | new_lead |
| Cory Handshoe | 3202665497 | Irrigation Refurbish | repair | Scheduled | estimate_scheduled | existing_lead |
| Richard | 9524651090 | Irrigation Addition | repair | Pending Response | schedule_estimate | new_lead |
| Sandeep Patwardhan | 7637428740 | Irrigation refurbish or New Install | new_installation | Scheduled | estimate_scheduled | existing_lead |
| David Rischall | 6512303911 | New System Install | new_installation | Scheduled | estimate_scheduled | existing_lead |
| Mark Herzog | 6125583633 | System Refurbish | repair | Scheduled | estimate_scheduled | existing_lead |
| Abby Gemmill | 5074590251 | System Update/Addition | repair | Scheduled | estimate_scheduled | new_lead |

**Notes**: Each SalesEntry preserves the original Excel status text and follow-up history in the `notes` field.

---

## Phase 3: Lead Cleanup

| Metric | Count |
|---|---|
| Leads with customer_id — status fixed to "converted" | 21 |
| Leads phone-matched to customers and converted | 4 |
| Total leads cleaned up | 25 |
| Remaining active leads | 15 |

### 21 Leads Fixed (had customer_id, status updated to "converted")

Brandon Peterson, Jason Skolak, Maria Starchook-Moore, Paul Doppmann, Brooke Jore, Charles Shelton, Jim Sterner, Derrick Washington, Patricia Bruns, Tricia Braun, Jeremy Brandt, Greg Alexander, Ken Lawrence, Dorthy Croskey, Mary Didbold, Cory Handshoe, Richard, Sandeep Patwardhan, David Rischall, Mark Herzog, Abby Gemmill

### 4 Leads Phone-Matched to Customers and Converted

| Lead Name | Matched Customer |
|---|---|
| Kevin Frawley | Kevin M Frawley |
| Jack Morgan | Jack Morgan |
| Sid Sen | Siddhartha Sen |
| Pidarpan | Viktor(test) Grin |

### 15 Remaining Active Leads (Unconnected — Kept As-Is)

| Name | Phone | Status |
|---|---|---|
| Ryan Lada | 6124753280 | new |
| Viktor Grin | +19528181020 | new |
| Kirill Rakitin | +19527373312 | new |
| Ian Kabitz | 7636077692 | new |
| Angela Cavalier | 6124791243 | new |
| Abby Gemmill | 5074560251 | new |
| Kirill Rakitin | 9527373311 | new |
| asad asad | 2045652473 | contacted |
| Dave | 6129407550 | contacted |
| Unknown | 0000000000 | contacted |
| Derek Davidsons | 7868692332 | contacted |
| Jenny Adams Salmela | 6127152556 | contacted |
| Kollie Ballah | 7637328246 | contacted |
| Ronald martin | 9132229866 | contacted |
| Steven Cornfield | 2488604846 | contacted |

---

## Phase 4: Verification

### Campaign Responses

| Metric | Value |
|---|---|
| Total campaign responses | 2 |
| With customer_id | 0 |
| Orphans (no customer_id) | 2 |

Both orphan campaign responses are test entries that are matchable by phone:
- Viktor Grin (+19528181020) — MATCHABLE
- Kirill Rakitin (+19527373312) — MATCHABLE

### Service Agreements

| Metric | Value |
|---|---|
| Total agreements | 111 |
| Valid (customer exists and not deleted) | **111/111** |
| Invalid | **0** |
| With Stripe subscription ID | **111/111** |
| Without Stripe subscription | **0** |

All 111 service agreements are intact, valid, and backed by Stripe subscriptions. No data integrity issues.

### Remaining Active Leads

15 unconnected leads remain (see Phase 3 table above). These are genuine new leads from website forms and test entries that have no matching customer record.

---

## Items Requiring Manual Attention

### Immediate Action

1. **4 skipped rows (bad phones)** — Island home, Jesse Huebsch, Josh Franz, Samuel Goldfarb need manual entry with corrected phone numbers
2. **1 customer flagged** — Service Package = Yes but no service agreement exists. Needs manual agreement setup in the CRM.

### Upcoming Action

3. **106 TBD customers** need a mass contact campaign to confirm whether they want spring 2026 service and when. All are flagged in `internal_notes` with `[MIGRATION] TBD scheduling - needs outreach`. Jobs are created as `to_be_scheduled` with null target dates.

### Informational

4. **2 campaign response orphans** — both are test entries (Viktor Grin and Kirill Rakitin), not real customers. No action needed.
5. **15 remaining active leads** — genuine unconnected leads. No cleanup needed; they should stay in the leads pipeline.

---

## Data Mappings Used

### Job Type Mapping (Excel -> Database)

| Excel Value | DB job_type | DB category |
|---|---|---|
| Spring Start Up | spring_startup | ready_to_schedule |
| New System Installation | new_installation | requires_estimate |
| Addition & Repair | repair | requires_estimate |
| Repairs & Additions | repair | requires_estimate |
| Drain Install | installation | requires_estimate |
| Sprinkler Head Repair | small_repair | ready_to_schedule |
| Supply Pipe Repair (Special Part) | repair | requires_estimate |
| Controller Install | installation | requires_estimate |
| Valve Location | diagnostic | ready_to_schedule |
| Start Up & Landscaping | spring_startup | ready_to_schedule |
| Start Up, zone intall, and controller | spring_startup | ready_to_schedule |
| Landscpaing & Irrigaiton | installation | requires_estimate |
| Finish System Install | installation | requires_estimate |
| Irrigation Install | new_installation | requires_estimate |
| Sod & Irrigation Install | new_installation | requires_estimate |
| Sod Install | installation | requires_estimate |
| Irrigation Refurbish | repair | requires_estimate |
| Irrigation & landscaping | installation | requires_estimate |
| Irrigation Addition | repair | requires_estimate |
| New System Install | new_installation | requires_estimate |
| System Refurbish | repair | requires_estimate |
| System Update/Addition | repair | requires_estimate |

### Property Type Mapping

| Excel Value | DB property_type | is_hoa |
|---|---|---|
| Residential | residential | false |
| Commercial | commercial | false |
| HOA | commercial | true |

### Sales Pipeline Status Mapping

| Excel Status | DB SalesEntry status |
|---|---|
| Pending Response | schedule_estimate |
| Scheduled | estimate_scheduled |
| All other statuses | schedule_estimate |

---

## Technical Details

- **Phone normalization**: All phones stored as 10-digit strings without +1 prefix. Excel floats (e.g. 6129900255.0), dashes, dots, and parentheses stripped. 11-digit numbers starting with 1 have country code removed. Concatenated dual numbers (20+ digits) use first 10 digits.
- **Name splitting**: Last space splits first/last name. Single-word names use same value for both.
- **Deduplication**: Phone is the unique key for customers. Properties deduped by customer_id + lowercase address. Jobs deduped by customer_id + job_type + property_id (excluding completed/cancelled).
- **Idempotency**: Script is safe to run multiple times. All INSERTs are guarded by SELECT checks. SAVEPOINTs used for per-row rollback on failure.
- **Transaction**: All changes committed in a single PostgreSQL transaction.
