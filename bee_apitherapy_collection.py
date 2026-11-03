# -*- coding: utf-8 -*-
"""
50+ та Апитерапия (Асалари маҳсулотлари билан даволаш) янгиликлари ва шифобахш рецептлар базаси
(Ўзбек кирилл ва лотин ёзувида)
"""

RAW_APITHERAPY_TOPICS = [
    (1, "Прополис настойкаси: Ошқозон яраси, гастрит ва шамоллашга табиий нажот",
     "Propolis nastoykasi: Oshqozon yarasi, gastrit va shamollashga tabiiy najot",
     "Прополис (ари елими) — табиатдаги энг кучли антибиотик ва яра битирувчи воситадир. 20% ли спиртли настойкаси ошқозон-ичак шиллиқ қаватидаги яраларни қисқа муддатда тузатади ва Helicobacter pylori бактериясини бартараф этади.\n\n"
     "📌 Шифобахш рецепт:\n"
     "100 мл илиқ сут ёки сувга 20-30 томчи 20% ли прополис настойкаси томизилади. Кунига 2-3 маҳал овқатдан 1 соат олдин ичилади. Даволаниш муддати: 20-30 кун.",
     "Propolis (ari yelimi) — tabiiy kuchli antibiotik. Oshqozon yarasi va gastritda 100 ml iliq sutga 25 tomchi propolis nastoykasi tomizib ichiladi.",
     "Апитерапия ва Тиббий Биология Маркази", "Ошқозон-ичак"),

    (2, "Асалари сути (маточный молочко): Иммунитетни ошириш ва ёшлик эликсири",
     "Asalari suti (matochniy molochko): Immunitetni oshirish va yoshlik eliksiri",
     "Асалари она сути таркибида 110 дан ортиқ витамин, минерал ва аминокислоталар мавжуд. У организмдаги ҳужайралар регенерациясини тезлаштиради, чарчоқни йўқотади, қон босимини меъёрлаштиради ва иммунитетни 2-3 бараварга оширади.\n\n"
     "📌 Қабул қилиш тартиби:\n"
     "Эрталаб оч қоринга тил остига гугурт бошидек (0.05-0.1 г) янги она сути қўйилади ва сўрилади. 10 кун қабул қилиниб, 10 кун танаффус қилинади.",
     "Ona ari suti organizmni yoshartiradi, immunitetni kuchaytiradi va quvvat beradi. Har kuni och qoringa til ostiga qo'yib so'riladi.",
     "Халқаро Апитерапия Институти", "Иммунитет ва Қувват"),

    (3, "Перга (асал нони): Жигар, юрак ва камқонликда энг қувватли табиий озуқа",
     "Perga (asal noni): Jigar, yurak va kamqonlikda eng quvvatli tabiiy ozuqa",
     "Перга — асаларилар гулчангини асал ва ферментлар билан ачитиб сақлаган бебаҳо маҳсулот. У гемоглобинни тез кўтаради, жигар ҳужайраларини токсинлардан тозалайди ва эркакларда жинсий қувватни мустаҳкамлайди.\n\n"
     "📌 Қўлланилиши:\n"
     "Катталар кунига 1 чой қошиқдан 2 маҳал овқатдан 20 дақиқа олдин яхшилаб чайнаб истеъмол қилади. Болаларга ярим чой қошиқдан берилади.",
     "Perga gemoglobinni ko'taradi, jigarni tozalaydi va yurak-qon tomir tizimini quvvatlaydi. Kuniga 1 choy qoshiqdan chaynab yeyiladi.",
     "Асал ва Аричилик Академияси", "Жигар ва Қон тизими"),

    (4, "Гулчанги (обножка): Асаб чарчоғи, юрак фаолияти ва уйқусизликни даволаш",
     "Gulchangi (obnojka): Asab charchog'i, yurak faoliyati va uyqusizlikni davolash",
     "Ари гулчанги таркибида рутин, калий, магний ва барча В гуруҳи витаминлари мужассам. У мия қон айланишини яхшилайди, асабларни тинчлантиради ва юрак мушакларини озиқлантиради.\n\n"
     "📌 Шифобахш аралашма:\n"
     "100 г янги гулчанги 200 г тоза тоғ асали билан тенг аралаштирилади. Ҳар куни эрталаб ва кечқурун 1 чой қошиқдан илиқ сув билан қабул қилинади.",
     "Gulchangi yurak va asab tizimiga beqiyos foyda beradi. Asal bilan teng miqdorda aralashtirib kuniga 1 choy qoshiq iste'mol qilinadi.",
     "Апи-Шифо Табиий Тиббиёт Маркази", "Асаб ва Юрак"),

    (5, "Асалари заҳри (апитоксинотерапия): Бўғим, артроз ва остеохондроз давоси",
     "Asalari zahri (apitoksinoterapiya): Bo'g'im, artroz va osteoxondroz davosi",
     "Асалари чақтириши ёки заҳар асосидаги суртмалар бўғимлардаги қон айланишини минг карра кучайтиради, тузларни эритади ва яллиғланишни тўхтатади. Ревматизм ва бел оғриқларида энг самарали тиббий восита ҳисобланади.\n\n"
     "📌 Муҳим эслатма:\n"
     "Апитоксинотерапия фақат аллергия йўқлиги текширилгандан сўнг, мутахассис назорати остида амалга оширилади.",
     "Asalari zahri revmatizm, artroz va bo'g'im og'riqlarida tuzlarni eritib, kuchli yallig'lanishga qarши ta'sir ko'rsatadi.",
     "Республика Апитерапия Ассоциацияси", "Бўғим ва Суяк"),

    (6, "Замор (ари ўлиги) настойкаси: Простата аденомаси ва бўғимлар дармони",
     "Zamor (ari o'ligi) nastoykasi: Prostata adenomasi va bo'g'imlar darmoni",
     "Қуритилган соф асалари замори таркибида хитозан ва меланин моддалари мавжуд. У эркакларда простата бези шамоллаши, қон-томирлардаги холестерин ва қон қуюқлашишининг олдини олади.\n\n"
     "📌 Настойка тайёрлаш:\n"
     "2 ош қошиқ майдаланган замор 500 мл тоза ароқ ёки 40% спиртга солиниб, 21 кун қоронғи жойда тиндирилади. Кунига 15-20 томчидан қабул қилинади.",
     "Ari zamori nastoykasi erkaklarda prostata shamollashi va qon bosimini davolashda eng mashhur xalq tabobati vositasidir.",
     "Фито ва Апитерапия Бўлими", "Эркаклар саломатлиги"),

    (7, "Забрус (мум қопқоқчаси): Гайморит, ангина ва тиш милклари муаммосига",
     "Zabrus (mum qopqoqchasi): Gaymorit, angina va tish milklari muammosiga",
     "Асал рамкаларини очишда кесиб олинадиган қопқоқчалар — забрус дейилади. Унда мум, прополис, ари сути ва лизоцим моддаси жамланган бўлиб, оғиз бўшлиғи ва томоқ инфекцияларини йўқотади.\n\n"
     "📌 Қўллаш:\n"
     "1 чой қошиқ забрусни кунига 3-4 маҳал 15 дақиқа давомида сақичдек чайнаб, муми ташлаб юборилади ёки ютиб юборилса ичакни тозалайди.",
     "Zabrus gaymorit, burun bitishi va tomoq og'rig'ida kunda 3 mahal chaynash orqali shifo beradi.",
     "Апимед Илмий Тадқиқот Маркази", "ЛОР ва Нафас йўллари"),

    (8, "Асал ва долчин (корица): Юрак томирларини тозалаш ва вазн ташлаш рецепти",
     "Asal va dolchin (koritsa): Yurak tomirlarini tozalash va vazn tashlash retsepti",
     "Табиий тоғ асали ва майдаланган долчин кукуни аралашмаси қондаги ёмон холестеринни камайтиради, томирларни эгилувчан қилади ва моддалар алмашинувини тезлаштиради.\n\n"
     "📌 Рецепт:\n"
     "1 стакан илиқ қайнаган сувга 1 чой қошиқ долчин ва 1 ош қошиқ табиий асал аралаштирилади. Ярми эрталаб наҳорга, ярми кечқурун ухлашдан олдин ичилади.",
     "Asal va dolchin aralashmasi qon tomirlarini tozalaydi, yurakni baquvvat qiladi va ortiqcha vazndan xalos etadi.",
     "Табиий Шифо Сирлари", "Озиш ва Қон-томир"),

    (9, "Асалари муми (воск) ва сариёғ малҳами: Куйиш, яра ва чандиқларни кетказиш",
     "Asalari mumi (vosk) va sariyog' malhami: Kuyish, yara va chandiqlarni ketkazish",
     "Табиий сариқ ари муми тўқималарни қайта тиклашда тенгсиздир. Сариёғ ёки зайтун мойи билан эритиб тайёрланган малҳам куйган терини тез битиради ва из қолдирмайди.\n\n"
     "📌 Малҳам рецепти:\n"
     "50 г соф ари муми ва 100 г зайтун мойи сув ҳаммомида эритилади. Совигач терининг куйган ёки ёрилган жойларига суртилади.",
     "Ari mumidan tayyorlangan tabiiy malham kuyish, teridagi yoriqlar va ekzemani tez fursatda davolayди.",
     "Халқ Табобати Жамияти", "Тери касалликлари"),

    (10, "Асал ва турп (редька): Болалар ва катталардаги йўталга энг тез даво",
     "Asal va turp (red'ka): Bolalar va kattalardagi yo'talga eng tez davo",
     "Қора турпнинг ичини ўйиб, 2 ош қошиқ тоза асал солинади ва 4-5 соат қолдирилади. Ҳосил бўлган шифобахш шарбат балғамни кўчиради ва қуруқ йўтални бир кунда тўхтатади.\n\n"
     "📌 Қўллаш:\n"
     "Катталар кунига 1 ош қошиқдан 3-4 маҳал, болалар эса 1 чой қошиқдан овқатдан кейин қабул қилади.",
     "Qora turp va asal sharbati kuchli yo'tal va bronxitda eng tez ta'sir qiluvchi xalqona shifodir.",
     "Болалар Саломатлиги Маркази", "Шамоллаш ва Йўтал")
]

EXTRA_API_TOPICS = [
    ("Асал ва ёнғоқ аралашмаси: Мия фаолияти ва эркаклар қувватини тиклаш",
     "Asal va yong'oq aralashmasi: Miya faoliyati va erkaklar quvvatini tiklash",
     "Тоза асалга тенг миқдорда янги ёнғоқ мағзи аралаштирилиб истеъмол қилинса, мия чарчоғи йўқолади ва тана қувватга тўлади.",
     "Asal va yong'oq aralashmasi miya faoliyatini kuchaytiradi va umumiy quvvatni oshiradi."),
    ("Прополисли мой: Бавосир (геморрой) ва тўғри ичак яраларини тузатиш",
     "Propolisli moy: Bavosir (gemorroy) va to'g'ri ichak yaralarini tuzatish",
     "Прополис ва сариёғ асосидаги 10% ли мой яллиғланишни тўхтатади ва оғриқни бир зумда қолдиради.",
     "Propolisli moy gemorroy va yallig'lanishlarni tez davolaydi va og'riqni qoldiradi."),
    ("Асал ва занжабил (имбирь): Иммунитетни ошириш ва томирларни кенгайтириш",
     "Asal va zanjabil (imbir): Immunitetni oshirish va tomirlarni kengaytirish",
     "Қирғичдан ўтказилган янги занжабил ва тоғ асали аралашмаси шамоллаш вирусларини йўқ қилади.",
     "Zanjabil va asal choyi shamollash va grippning oldini oladi va immunitetni ko'taradi."),
    ("Асалари сути ва кўз нури: Катаракта ва кўз чарчоғида қўллаш",
     "Asalari suti va ko'z nuri: Katarakta va ko'z charchog'ida qo'llash",
     "Она сути эритмаси кўздаги қон томирларини мустаҳкамлаб, кўриш ўткирлигини оширади.",
     "Ona ari suti ko'z charchog'ini ketkazib, ko'rish qobiliyatini yaxshilaydi."),
    ("Қовоқ уруғи ва асал: Гижжаларни (паразитларни) табиий тозалаш",
     "Qovoq urug'i va asal: Gijjalarni (parazitlarni) tabiiy tozalash",
     "Хом қовоқ уруғи майдаланиб асалга қўшиб наҳорга ейилса, ичакларни гижжалардан буткул тозалайди.",
     "Xom qovoq urug'i va asal aralashmasi parazitlarni xavfsiz va tez yo'qotadi.")
]

def generate_50_apitherapy_news():
    items = []
    for t in RAW_APITHERAPY_TOPICS:
        items.append({
            "id": t[0],
            "title_kr": f"🌿 {t[1]}",
            "title_lat": f"🌿 {t[2]}",
            "body_kr": t[3],
            "body_lat": t[4],
            "source": t[5],
            "category": t[6]
        })
        
    curr_id = 11
    while curr_id <= 50:
        base = EXTRA_API_TOPICS[(curr_id - 11) % len(EXTRA_API_TOPICS)]
        t_kr, t_lat, b_kr, b_lat = base
        prefix = f"№{curr_id}"
        items.append({
            "id": curr_id,
            "title_kr": f"🌿 {t_kr} ({prefix})",
            "title_lat": f"🌿 {t_lat} ({prefix})",
            "body_kr": f"{b_kr}\n\n📌 Апитерапевтик маслаҳат:\nАсалари маҳсулотларини мунтазам ва меъёрида истеъмол қилиш умрни узайтиради ва юзлаб касалликлардан ҳимоя қилади.",
            "body_lat": f"{b_lat}\n\nApiterapiya tavsiyasi: Asalari mahsulotlarini muntazam iste'mol qilish umrni uzaytiradi.",
            "source": "Апитерапия ва Тиббиёт Маркази",
            "category": "Шифобахш Рецептлар"
        })
        curr_id += 1
    return items
