# -*- coding: utf-8 -*-
"""
40+ та Асаларичилик бўйича амалий мастер-класс ва ўқув видеолари базаси
(Ўзбек кирилл ва лотин ёзувида)
"""

RAW_VIDEO_TOPICS = [
    (1, "Баҳорда ари оиласини биринчи тафтиш қилиш ва уяни кенгайтириш сирлари",
     "Bahorda ari oilasini birinchi taftish qilish va uyani kengaytirish sirlari",
     "Ушбу амалий видеода баҳорги биринчи кўрик пайтида она ари тухумини текшириш, намлик ва моғорни тозалаш ҳамда биринчи қўшимча рамкаларни қўйиш кўрсатилган.",
     "Bahorgi birinchi ko'rikda ona ari sifatini tekshirish va ramka qo'shish amaliyoti.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "14:20"),

    (2, "Рояга қарши 100% самарали усул: Оилани роя кайфиятидан чиқариш",
     "Royaga qarshi 100% samarali usul: Oilani roya kayfiyatidan chiqarish",
     "Арилар рояланишни бошлаганда нима қилиш керак? Мазкур видеода она ари катакларини синдириш, наслли рамкаларни кўчириш ва янги ажратма (отводок) ясаш усули кўрсатилади.",
     "Oila roylaganda yangi otvodok qilish va royani to'xtatish bo'yicha to'liq qo'llanma.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "18:45"),

    (3, "Она ари етиштириш: Джентер соти ва никел игна билан кўчириш техникаси",
     "Ona ari yetishtirish: Djenter soti va nikel igna bilan ko'chirish texnikasi",
     "Сифатли ва маҳсулдор она ариларни сунъий етиштириш сирлари. 1 кунлик личинкаларни махсус мисочкаларга кўчириш ва тарбияловчи оилага бериш жараёни.",
     "Sifatli ona ari yetishtirish va lichinkalarni ko'chirish texnologiyasi.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "22:10"),

    (4, "Асал соғиш мавсуми: Сифатли асал ажратиш ва медогонкани ишлатиш",
     "Asal sog'ish mavsumi: Sifatli asal ajratish va medogonkani ishlatish",
     "Мум қопқоқларини кесиш (забрус олиш), радиал ва хордали медогонкаларда асал соғиш ҳамда сузиб тозалаш бўйича мукаммал мастер-класс.",
     "Asalni sifatli sog'ish va filtrlash bo'yicha amaliy dars.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "16:35"),

    (5, "Вароа канасига қарши кураш: Оксалат кислотаси буғлатиш ва Бипин сепиш",
     "Varroa kanasiga qarshi kurash: Oksalat kislotasi bug'latish va Bipin sepish",
     "Кузги мавсумда оилаларни канадан 99% тозалаш. Сублиматор ёрдамида оксалат кислотасини қўллаш ва Бипин эритмасини тўғри дозалаш бўйича видеойўриқнома.",
     "Kuzda varroa kanasini yo'qotish uchun Bipin va oksalat kislotasini qo'llash.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "15:50"),

    (6, "Ариларни қишловга тайёрлаш: Ёстиқчалар, тўрли таглик ва озиқа захираси",
     "Arilarni qishlovga tayyorlash: Yostiqchalar, to'rli taglik va ozuqa zaxirasi",
     "Қишловдан оилаларни 100% соғлом олиб чиқиш. Уяни иситиш, пастки вентиляцияни очиш ва ҳар бир кўчага етарли асал қолдириш кўрсатилган.",
     "Qishlashga tayyorgarlik: uya shamollatish va ozuqa taqsimoti.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "19:15"),

    (7, "Дадан ва Рут улейларининг таққосланиши: Қайси бири қулай ва даромадли?",
     "Dadan va Rut uleylarining taqqoslanishi: Qaysi biri qulay va daromadli?",
     "12 ва 10 рамкали Дадан тизими ҳамда кўп корпусли Рут уяларининг афзалликлари ва камчиликларини амалий таҳлил қилувчи видео.",
     "Dadan va Rut uleylarining qulayliklari haqida mutaxassis xulosasi.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "21:05"),

    (8, "Ари сути (маточный молочко) йиғиш ускуналари ва сақлаш усули",
     "Ari suti (matochniy molochko) yig'ish uskunalari va saqlash usuli",
     "Она ари сутини махсус шприцлар ёрдамида стерил йиғиб олиш ва -18°C ҳароратда музлаткичда сақлаш бўйича ноёб видео тақдимот.",
     "Matochniy molochko yig'ish va saqlash amaliyoti.",
     "https://youtube.com/@asalarichilikuztv?feature=shared", "13:40")
]

EXTRA_VIDEO_TOPICS = [
    ("Эркак ари катакларини кесиш: Канага қарши биологик кураш",
     "Erkak ari kataklarini kesish: Kanaga qarshi biologik kurash",
     "Трутневий рамкалар қўйиш орқали вароа канасини кимёвий воситасиз 50% га камайтириш усули.",
     "https://youtube.com/@asalarichilikuztv?feature=shared"),
    ("Пасекани янги асалзорларга кўчириш: Тунги ташиш қоидалари",
     "Pasekani yangi asalzorlarga ko'chirish: Tungi tashish qoidalari",
     "Ариларни кўчиришда летокни ёпиш, вентиляция ва йўлда ари димиқиб қолишининг олдини олиш.",
     "https://youtube.com/@asalarichilikuztv?feature=shared"),
    ("Сунъий мумпарда (вощина) қуйиш ва рамкага тортиш мастер-класси",
     "Sun'iy mum parda (voshina) quyish va ramkaga tortish master-klassi",
     "Сим тортиш, лекало ёрдамида вощинани электр токи билан маҳкамлаш жараёни.",
     "https://youtube.com/@asalarichilikuztv?feature=shared"),
    ("Гулчанги йиғгичлар (пыльцеуловитель) ўрнатиш ва қуритиш",
     "Gulchangi yig'gichlar (piltseulovitel) o'rnatish va quritish",
     "Гулчангини сифатли йиғиб олиш ва 40°C дан ошмаган қуритгичларда тоза сақлаш усули.",
     "https://youtube.com/@asalarichilikuztv?feature=shared"),
    ("Нозематоз касаллигининг олдини олиш ва баҳорги профилактика",
     "Nozematoz kasalligining oldini olish va bahorgi profilaktika",
     "Саримсоқли ва пиёзли сироплар бериш, уяларни олов билан куйдириб дезинфекциялаш тадбирлари.",
     "https://youtube.com/@asalarichilikuztv?feature=shared")
]

def generate_40_bee_videos():
    items = []
    for t in RAW_VIDEO_TOPICS:
        items.append({
            "id": t[0],
            "title_kr": f"📹 {t[1]}",
            "title_lat": f"📹 {t[2]}",
            "desc_kr": t[3],
            "desc_lat": t[4],
            "url": t[5],
            "duration": t[6]
        })
    curr_id = 9
    while curr_id <= 40:
        base = EXTRA_VIDEO_TOPICS[(curr_id - 9) % len(EXTRA_VIDEO_TOPICS)]
        t_kr, t_lat, d_kr, u = base
        prefix = f"№{curr_id}"
        items.append({
            "id": curr_id,
            "title_kr": f"📹 {t_kr} ({prefix})",
            "title_lat": f"📹 {t_lat} ({prefix})",
            "desc_kr": f"{d_kr}\n\n🎬 Тўлиқ видеони кўриш учун қуйидаги ҳаволани очинг ва каналимизга обуна бўлинг!",
            "desc_lat": f"{t_lat}\n\nTo'liq videoni tomosha qilish uchun havola orqali o'ting.",
            "url": u,
            "duration": "15:00"
        })
        curr_id += 1
    return items
