## Skjal 1
Fráboðanir til Vørn
Niðan fyri standandi fráboðanir skulu sendast Vørn í XML sniði umvegis heimasíðuna, www.vorn.fo, undir “Veiðifráboðanir”. Fráboðanir kunnu eisini sendast umvegis Elektronisku veiðidagbókina, sum er góðkend av Vørn.
1) COE - Fráboðan um, at fiskiskapur byrjar. Skal sendast, í fyrsta lagi 6 tímar og í seinasta lagi 2 tímar, áðrenn fiskiskapurin byrjar.
Fráboðanin skal hava fylgjandi tekst:
Dataelement | Koda | Frágreiðing
Fráboðan | TM | COE, fráboðan um, at fiskiskapur byrjar (Catch on Entry)
Raðnummar | SQ | Nummar á fráboðanini
Loyvisnummar | LC | Nummar á fiskiloyvi
Beinleiðis veiða | DS | Fiskaslag sum beinleiðis veiða er eftir
Radio kallimerki | RC | Kallimerki hjá skipinum
IMO nummar | IM | IMO nummar á skipinum (um tøkt)
Túranummar | TN | Túrur hjá skipinum í hesum árinum
Skip | NA | Navn á skipinum
Skipari | MA | Navn á skiparanum
Havnarkenningarnummar | XR | Havnarkenningarnummar hjá skipinum
Veiðiøki | RA | Økið hagar skipið fer til fiskiskap
Breiddarstig | LA | Knattstøða (N/S breidd), tá fráboðanin verður send
Longdarstig | LO | Knattstøða (E/V longd), tá fráboðanin verður send
Veiða umborð | OB | Veiða umborð flokkað eftir fiskasløgum (FAO 3 alpha kodu. Veiðan skal gevast upp í rundari vekt í kg.
Dagfesting | DA | Dagfesting, tá fráboðanin er send (dd-mm-yyyy)
Klokkutíð | TI | Klokkutíð, tá fráboðanin er send í UTC (24M h:m)
Viðmerkingar | RE | Viðmerkingar
2) CAT - Veiðifráboðan hvønn dag. Fráboðanin skal sendast, hóast eingin veiða er fingin. Skal sendast dagliga, tá fiskiskapurin fyri dagin er liðugur og í seinasta lagi kl. 12.00 UTC dagin eftir.
Fráboðanin skal hava fylgjandi tekst:
Dataelement | Koda | Frágreiðing
Fráboðan | TM | CAT, veiðifráboðan (Daily Catch report)
Raðnummar | SQ | Nummar á fráboðanini
Loyvisnummar | LC | Nummar á fiskiloyvi
Beinleiðis veiða | DS | Fiskaslag, sum beinleiðis veiða er eftir
Radio kallimerki | RC | Kallimerki hjá skipinum
IMO nummar | IM | IMO nummar á skipinum (um tøkt)
Túranummar | TN | Túrur hjá skipinum í hesum árinum
Skip | NA | Navn á skipinum
Skipari | MA | Navn á skiparanum
Havnarkenningarnummar | XR | Havnarkenningarnummar hjá skipinum
Veiðiøki | RA | Økið har skipið er til fiskiskap
Breiddarstig | LA | Knattstøða (N/S breidd), tá fráboðanin verður send
Longdarstig | LO | Knattstøða (E/V longd), tá fráboðanin verður send
Veiða | CA | Veiða undanfarna samdøgur frá 00.00 til 23.59(CAT), flokkað eftir fiskasløgum (FAO 3 alpha kodu). Veiðan skal gevast upp í rundari vekt í kg.
Samlað veiða umborð | TC | Samlað veiða umborð (FAO 3 alpha kodu), í rundari vekt í kg.
Dagfesting | DA | Dagfesting, tá fráboðanin er send (dd-mm-yyyy)
Klokkutíð | TI | Klokkutíð, tá fráboðanin er send í UTC (24H h:m)
Viðmerkingar | RE | Viðmerkingar
3) COX - Fráboðan um, at fiskiskapur endar. Skal sendast beinanvegin skipið gevst at fiska.
Fráboðanin skal hava fylgjandi tekst:
Dataelement | Koda | Frágreiðing
Fráboðan | TM | COX, fráboðan, at fiskiskapur endar (Catch on Exit)
Raðnummar | SQ | Nummar á fráboðanini
Loyvisnummar | LC | Nummar á fiskiloyvi
Beinleiðis veiða | DS | Fiskaslag, sum beinleiðis veiða hevur verið eftir
Radio kallimerki | RC | Kallimerki hjá skipinum
IMO nummar | IM | IMO nummar á skipinum (um tøkt)
Túranummar | TN | Túrur hjá skipinum í hesum árinum
Skip | NA | Navn á skipinum
Skipari | MA | Navn á skiparanum
Havnarkenningarnummar | XR | Havnarkenningarnummar hjá skipinum
Veiðiøki | RA | Økið hvaðani skipið kemur av fiskiskapi
Breiddarstig | LA | Knattstøða (N/S breidd), tá fráboðanin verður send
Longdarstig | LO | Knattstøða (E/V longd), tá fráboðanin verður send
Veiða | CA | Veiða, fiskað undanfarna samdøgur frá 00.00-23.59, flokkað eftir fiskasløgum (FAO 3 alpha kodu). Veiðan skal gevast upp í rundari vekt í kg.
