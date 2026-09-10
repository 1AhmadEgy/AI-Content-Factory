from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..domain.characters import CharacterProfile
from ..domain.locations import LocationProfile
from ..domain.projects import Project

DEFAULT_LIBRARY_PROJECT_ID = "local-library-egypt"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _location(id: str, name: str, category: str, description: str, city: str, aliases: tuple[str, ...] = (), **data: Any) -> LocationProfile:
    now = _now()
    return LocationProfile(
        id=id, project_id=DEFAULT_LIBRARY_PROJECT_ID, name=name, aliases=aliases, description=description,
        geography={"country":"Egypt", "city":city, **data.pop("geography", {})},
        architecture=data.pop("architecture", {}), environment=data.pop("environment", {}),
        visual_style=data.pop("visual_style", {"detail":"cinematic realism", "period":"location-consistent"}),
        lighting=data.pop("lighting", {"day":"natural light", "night":"practical cinematic lighting"}),
        weather=data.pop("weather", {"default":"clear and realistic", "alternate":"light haze"}),
        time_of_day=data.pop("time_of_day", "day"), props=tuple(data.pop("props", ())),
        rules=tuple(data.pop("rules", ("preserve recognizable geometry and scale", "keep continuity between shots"))),
        negative_constraints=tuple(data.pop("negative_constraints", ("no fantasy architecture", "no futuristic elements unless requested"))),
        reference_asset_ids=(), provider_location_id=None,
        metadata={"library":"default-egypt", "category":category, "ready":True, **data},
        version=1, created_at=now, updated_at=now,
    )


def default_locations() -> list[LocationProfile]:
    return [
        _location("loc-egypt-giza-pyramids", "أهرامات الجيزة", "تاريخي", "مجمع الأهرامات والصحراء المحيطة به، مناسب للمغامرة والتاريخ والدراما.", "الجيزة", ("Pyramids of Giza",), architecture={"era":"Ancient Egypt","structures":["pyramids","Sphinx","stone temples"]}, environment={"terrain":"desert plateau","ground":"sand and limestone","crowd":"tourists and guides"}, visual_style={"detail":"epic archaeological realism","palette":"sandstone and sky blue"}, lighting={"day":"hard warm sun","sunset":"golden rim light","night":"cool moonlight"}, time_of_day="golden hour", props=("camels","tourist buses","guide flags","stone blocks")),
        _location("loc-egypt-sphinx", "أبو الهول", "تاريخي", "الساحة الأثرية أمام تمثال أبو الهول مع الأهرامات في الخلفية.", "الجيزة", ("Great Sphinx",), architecture={"era":"Old Kingdom","structures":["Sphinx","temple ruins","limestone walls"]}, environment={"terrain":"rock-cut archaeological court","ground":"limestone"}, props=("tourist barriers","stone fragments","guide signs")),
        _location("loc-egypt-khan-el-khalili", "خان الخليلي", "سوق شعبي", "أزقة القاهرة القديمة بالمحال والحرف والفوانيس والحركة الشعبية.", "القاهرة", ("Khan el-Khalili",), architecture={"era":"historic Islamic Cairo","structures":["stone arcades","wooden shopfronts","ornamental facades"]}, environment={"terrain":"dense historic lanes","crowd":"busy pedestrians"}, lighting={"day":"filtered sunlight","night":"warm shop lanterns"}, time_of_day="evening", props=("lanterns","brassware","textiles","wooden doors","Arabic signs")),
        _location("loc-egypt-cairo-citadel", "قلعة صلاح الدين بالقاهرة", "تاريخي", "قلعة مرتفعة بجدران حجرية وساحات ومساجد تاريخية وإطلالات على القاهرة.", "القاهرة", ("Cairo Citadel",), architecture={"era":"medieval Islamic","structures":["fortification walls","domes","minarets","courtyards"]}, environment={"terrain":"elevated limestone hill","view":"Cairo skyline"}, time_of_day="sunset", props=("stone walls","flags","wooden doors","courtyard lamps")),
        _location("loc-egypt-museum", "المتحف المصري بالقاهرة", "متحف", "قاعات متحف بطابع كلاسيكي وآثار مصرية قديمة.", "القاهرة", ("Egyptian Museum",), architecture={"style":"neoclassical","interior":"high ceilings and galleries"}, environment={"crowd":"museum visitors","displays":"ancient artifacts"}, lighting={"interior":"soft diffuse gallery light","display":"controlled spot lighting"}, props=("display cases","statues","hieroglyphic panels","museum labels")),
        _location("loc-egypt-ramses-station", "محطة مصر - رمسيس", "محطة قطار", "محطة قطارات مركزية مناسبة للسفر والوصول والمطاردات والمشاهد اليومية.", "القاهرة", ("Ramses Station",), architecture={"style":"historic railway architecture","structures":["large concourse","platform canopies","station facade"]}, environment={"crowd":"busy travelers","transport":"trains and taxis","ground":"platform concrete and stone"}, lighting={"day":"bright skylight","night":"platform and station lamps"}, time_of_day="late afternoon", props=("trains","platform signs","luggage","ticket counters","clocks"), negative_constraints=("no futuristic trains","no metro-only architecture")),
        _location("loc-egypt-sidi-gaber", "محطة سيدي جابر - الإسكندرية", "محطة قطار", "محطة قطار حضرية ساحلية لمشاهد السفر والمغادرة والوصول.", "الإسكندرية", ("Sidi Gaber Station",), architecture={"style":"Egyptian railway station","structures":["platforms","station hall","canopies"]}, environment={"terrain":"coastal urban","crowd":"travelers"}, props=("train cars","luggage carts","platform signs","coffee kiosks")),
        _location("loc-egypt-azhar-park", "حديقة الأزهر", "حديقة", "حديقة مرتفعة خضراء بإطلالات على القاهرة التاريخية.", "القاهرة", ("Al-Azhar Park",), architecture={"style":"landscape architecture with Islamic references","structures":["terraces","walkways","water features"]}, environment={"vegetation":"lush gardens","crowd":"families and walkers","view":"historic Cairo"}, visual_style={"detail":"cinematic garden realism","palette":"green, limestone and warm earth"}, props=("trees","benches","fountains","stone paths","lamps")),
        _location("loc-egypt-nile-corniche", "كورنيش النيل بالقاهرة", "مدينة", "طريق وممشى بمحاذاة النيل مع حركة السيارات والقوارب وإضاءة المدينة.", "القاهرة", ("Cairo Nile Corniche",), environment={"terrain":"riverfront urban corridor","water":"Nile River","traffic":"busy"}, lighting={"day":"bright urban light","night":"mixed street and building lights"}, time_of_day="night", props=("cars","taxis","river boats","street lamps","bridge lights"), negative_constraints=("no ocean waves","no futuristic skyline")),
        _location("loc-egypt-alex-corniche", "كورنيش الإسكندرية", "ساحل", "واجهة بحرية متوسطية تجمع البحر والطريق والمباني الحضرية.", "الإسكندرية", ("Alexandria Corniche",), environment={"terrain":"Mediterranean coast","water":"Mediterranean Sea","traffic":"cars and pedestrians"}, lighting={"day":"strong coastal sun","sunset":"warm horizon","night":"street lights"}, time_of_day="sunset", props=("cars","fishing boats","benches","lamps","sea wall")),
        _location("loc-egypt-luxor-temple", "معبد الأقصر", "تاريخي", "معبد مصري قديم مناسب للمشاهد التاريخية والدرامية الملحمية.", "الأقصر", ("Luxor Temple",), architecture={"era":"Ancient Egypt","structures":["pylons","columns","statues","courtyards"]}, environment={"ground":"stone","vegetation":"palms nearby"}, visual_style={"detail":"monumental historical realism","palette":"golden sandstone"}, lighting={"day":"hard desert sun","sunset":"deep golden light"}, time_of_day="sunset", props=("columns","statues","stone blocks")),
        _location("loc-egypt-karnak", "مجمع معابد الكرنك", "تاريخي", "مجمع أثري ضخم من الأعمدة والصروح والساحات في الأقصر.", "الأقصر", ("Karnak Temple",), architecture={"era":"Ancient Egypt","structures":["hypostyle hall","pylons","obelisks","statues"]}, environment={"ground":"stone and sand","scale":"monumental"}, visual_style={"detail":"epic historical realism","palette":"sandstone gold and deep shadow"}, props=("columns","obelisks","statues","stone fragments")),
        _location("loc-egypt-white-desert", "الصحراء البيضاء", "طبيعة", "تكوينات صخرية بيضاء نحتتها الرياح في الصحراء الغربية.", "الفرافرة", ("White Desert",), environment={"terrain":"chalk desert","vegetation":"very sparse","landmarks":"wind-sculpted formations"}, visual_style={"detail":"wide cinematic landscape","palette":"white chalk, beige sand, blue sky"}, lighting={"day":"strong sun","sunset":"warm low-angle light","night":"moonlit desert"}, time_of_day="sunset", props=("4x4 vehicles","camp chairs","lanterns")),
        _location("loc-egypt-fayoum-oasis", "واحة الفيوم", "طبيعة", "واحة تجمع النخيل والمياه والأراضي الزراعية والصحراء.", "الفيوم", ("Fayoum Oasis",), environment={"terrain":"oasis basin","vegetation":"date palms and crops","water":"irrigation channels"}, visual_style={"detail":"naturalistic Egyptian countryside","palette":"green against desert ochre"}, time_of_day="sunrise", props=("palm trees","water channels","farm tools")),
        _location("loc-egypt-alexandria-library", "مكتبة الإسكندرية", "ثقافي", "مركز ثقافي حديث على البحر بتصميم معماري مميز.", "الإسكندرية", ("Bibliotheca Alexandrina",), architecture={"style":"modern monumental","structures":["sloped circular roof","stone facade","glass volumes"]}, environment={"crowd":"students and visitors","water":"Mediterranean nearby"}, visual_style={"detail":"clean architectural realism"}, props=("books","desks","reading lamps","stone panels")),
    ]


def _character(id: str, name: str, category: str, description: str, personality: dict[str, Any], appearance: dict[str, Any], voice: dict[str, Any], speaking: dict[str, Any], visual: dict[str, Any], behavior: tuple[str, ...], aliases: tuple[str, ...] = ()) -> CharacterProfile:
    now = _now()
    return CharacterProfile(id=id, project_id=DEFAULT_LIBRARY_PROJECT_ID, name=name, aliases=aliases, description=description, personality=personality, appearance=appearance, voice=voice, speaking_style=speaking, visual_style=visual, behavior_rules=behavior, reference_asset_ids=(), provider_character_id=None, metadata={"library":"default-egypt","category":category,"ready":True}, version=1, created_at=now, updated_at=now)


def default_characters() -> list[CharacterProfile]:
    return [
        _character("char-egypt-felfel", "فلفل", "كوميديا", "شخصية كوميدية مصرية سريعة البديهة تتورط في المشاكل وتحاول الخروج منها بالكلام.", {"traits":["funny","optimistic","improviser"],"flaw":"overconfidence"}, {"age":"30s","build":"average","hair":"short dark hair","wardrobe":"casual Egyptian streetwear","signature":"expressive eyebrows"}, {"tone":"warm male comedy","pace":"fast","energy":"high"}, {"sentence_style":"short punchlines","humor":"situational","dialect":"Egyptian Arabic"}, {"palette":"bright casual","framing":"expressive medium shots"}, ("turn mistakes into jokes","use exaggerated reactions without changing identity","keep appearance stable"), ("FelFel",)),
        _character("char-egypt-basbousa", "بسبوسة", "كوميديا", "شخصية مرحة ذكية تستعمل الملاحظة والسخرية الخفيفة لحل المواقف.", {"traits":["clever","playful","observant"],"flaw":"impatience"}, {"age":"20s","build":"slim","hair":"curly dark hair","wardrobe":"colorful modern casual","signature":"confident smile"}, {"tone":"bright female comedy","pace":"medium-fast","energy":"high"}, {"sentence_style":"witty replies","humor":"light sarcasm","dialect":"Egyptian Arabic"}, {"palette":"vivid friendly","framing":"close reaction shots"}, ("lead with clever observations","keep humor light","maintain recognizable hairstyle")),
        _character("char-egypt-shokry", "عم شكري", "كوميديا", "رجل خمسيني طيب يبالغ في الثقة بخبرته ويعطي نصائح غير متوقعة.", {"traits":["kind","confident","storyteller"],"flaw":"overexplaining"}, {"age":"50s","build":"stocky","hair":"gray hair and mustache","wardrobe":"simple Egyptian clothing","signature":"round glasses"}, {"tone":"deep warm male","pace":"deliberate","energy":"medium"}, {"sentence_style":"long setup then punchline","humor":"anecdotes","dialect":"Egyptian Arabic"}, {"palette":"earthy","framing":"medium and group shots"}, ("always have an anecdote","stay friendly during arguments","never become threatening")),
        _character("char-egypt-tiger", "النمر", "قتال", "بطل أكشن أصلي هادئ ومحترف في القتال اليدوي ويعتمد على الدقة والتكتيك.", {"traits":["calm","disciplined","protective"],"flaw":"reserved"}, {"age":"30s","build":"athletic","hair":"short black hair","wardrobe":"dark practical jacket and cargo trousers","signature":"small eyebrow scar"}, {"tone":"low controlled male","pace":"measured","energy":"controlled"}, {"sentence_style":"short decisive lines","dialogue":"minimal","dialect":"Egyptian Arabic"}, {"palette":"dark neutral","framing":"dynamic readable action"}, ("protect civilians","use controlled non-graphic combat","keep choreography physically plausible","no gore")),
        _character("char-egypt-falcon", "الصقر", "قتال", "بطلة حركة سريعة تعتمد على المراوغة والذكاء التكتيكي.", {"traits":["agile","strategic","brave"],"flaw":"reckless"}, {"age":"late 20s","build":"athletic","hair":"dark ponytail","wardrobe":"practical urban action clothing","signature":"light scarf"}, {"tone":"confident female","pace":"fast in action","energy":"high"}, {"sentence_style":"direct","dialogue":"focused","dialect":"Egyptian Arabic"}, {"palette":"cool neutral","framing":"tracking shots"}, ("favor evasion and disarming","protect teammates","keep signature scarf","no gore")),
        _character("char-egypt-shadow", "الظل", "خصم", "خصم غامض هادئ يستخدم التخطيط والضغط النفسي بدل الصراخ.", {"traits":["calculating","patient","charismatic"],"flaw":"ego"}, {"age":"40s","build":"tall","hair":"dark","wardrobe":"tailored dark suit","signature":"black gloves"}, {"tone":"quiet authoritative male","pace":"slow","energy":"controlled"}, {"sentence_style":"precise","dialogue":"subtle threats","dialect":"Egyptian Arabic"}, {"palette":"charcoal and muted gold","framing":"symmetrical controlled shots"}, ("stay composed","avoid random violence","reveal motives gradually")),
        _character("char-egypt-younes", "المعلم يونس", "تحقيق", "محقق مخضرم يلاحظ التفاصيل الصغيرة ويجمع الأدلة بهدوء.", {"traits":["observant","patient","ethical"],"flaw":"skeptical"}, {"age":"40s","build":"average","hair":"short dark hair with gray","wardrobe":"simple shirt and light jacket","signature":"notebook"}, {"tone":"steady male","pace":"medium","energy":"focused"}, {"sentence_style":"questions and concise conclusions","dialogue":"logical","dialect":"Egyptian Arabic"}, {"palette":"muted realistic","framing":"closeups on clues"}, ("verify before accusing","protect innocent people","use notebook as recurring prop")),
        _character("char-egypt-marwan", "مروان", "مغامرة", "طفل فضولي شجاع يطرح الأسئلة التي تحرك القصة.", {"traits":["curious","brave","imaginative"],"flaw":"impulsive"}, {"age":"10","build":"small","hair":"short curly dark hair","wardrobe":"T-shirt and jeans","signature":"red backpack"}, {"tone":"young energetic","pace":"fast","energy":"high"}, {"sentence_style":"short questions","humor":"innocent","dialect":"Egyptian Arabic"}, {"palette":"bright adventure","framing":"child-height camera"}, ("ask questions instead of exposition","stay curious not reckless","keep red backpack consistent")),
        _character("char-egypt-zeinab", "الحاجة زينب", "دراما", "سيدة مصرية مسنة حكيمة تمثل ذاكرة المكان وتربط الأحداث بحكايات الماضي.", {"traits":["wise","warm","strong-minded"],"flaw":"stubborn"}, {"age":"70s","build":"average","hair":"covered","wardrobe":"modest traditional Egyptian clothing","signature":"wooden cane"}, {"tone":"warm elderly female","pace":"slow","energy":"calm"}, {"sentence_style":"proverbs and stories","dialect":"Egyptian Arabic"}, {"palette":"warm earthy","framing":"intimate portraits"}, ("use memory as a story device","remain kind but firm","keep cane consistent")),
        _character("char-egypt-narrator", "الراوي", "راوي", "راوٍ محايد يصلح للأفلام القصيرة والقصص الوثائقية والدرامية.", {"traits":["clear","curious","measured"]}, {"age":"adult","build":"voice-led","signature":"consistent narrator identity"}, {"tone":"neutral Egyptian narrator","pace":"medium","energy":"controlled"}, {"sentence_style":"clear descriptive sentences","dialect":"Egyptian Arabic"}, {"palette":"neutral","framing":"story-driven"}, ("separate narration from dialogue","avoid repeating visible information","maintain pronunciation consistency")),
    ]


def seed_default_library(runtime: Any) -> dict[str, int]:
    """Idempotently install the ready local Egypt library; never overwrite user edits."""
    projects = runtime.repositories.projects
    if projects.get(DEFAULT_LIBRARY_PROJECT_ID) is None:
        projects.create(Project(id=DEFAULT_LIBRARY_PROJECT_ID, name="المكتبة المحلية الجاهزة - مصر", description="مواقع وشخصيات جاهزة لإعادة الاستخدام في صناعة المحتوى.", settings={"systemLibrary":True,"country":"Egypt"}))
    locations_added = 0
    for item in default_locations():
        if runtime.locations.get(item.id) is None:
            runtime.locations.create(item)
            locations_added += 1
    characters_added = 0
    for item in default_characters():
        if runtime.characters.get(item.id) is None:
            runtime.characters.create(item)
            characters_added += 1
    return {"locationsAdded":locations_added,"charactersAdded":characters_added}
