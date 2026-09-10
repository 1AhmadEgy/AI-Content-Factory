from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ...domain.characters import CharacterProfile
from ...domain.locations import LocationProfile

LIBRARY_PROJECT_ID = "local-library-libya"
LIBRARY_VERSION = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _loc(
    id: str,
    name: str,
    city: str,
    description: str,
    *,
    aliases: tuple[str, ...] = (),
    geography: dict[str, Any] | None = None,
    architecture: dict[str, Any] | None = None,
    environment: dict[str, Any] | None = None,
    visual: dict[str, Any] | None = None,
    lighting: dict[str, Any] | None = None,
    time: str = "day",
    props: tuple[str, ...] = (),
    rules: tuple[str, ...] = (),
    negative: tuple[str, ...] = (),
) -> LocationProfile:
    now = _now()
    return LocationProfile(
        id=id,
        project_id=LIBRARY_PROJECT_ID,
        name=name,
        aliases=aliases,
        description=description,
        geography={"country": "Libya", "city": city, **(geography or {})},
        architecture=architecture or {},
        environment=environment or {},
        visual_style=visual or {"detail": "cinematic Libyan realism"},
        lighting=lighting or {"day": "natural Mediterranean/desert light", "night": "practical urban light"},
        weather={"default": "realistic local weather", "alternate": "dust or coastal haze when appropriate"},
        time_of_day=time,
        props=props,
        rules=rules or ("preserve recognizable geography and scale", "keep continuity between shots"),
        negative_constraints=negative or ("no invented landmarks presented as real", "no futuristic architecture unless requested"),
        reference_asset_ids=(),
        provider_location_id=None,
        metadata={"library": "libya", "ready": True, "libraryVersion": LIBRARY_VERSION},
        version=1,
        created_at=now,
        updated_at=now,
    )


def locations() -> list[LocationProfile]:
    return [
        _loc("loc-libya-tripoli-old-city", "المدينة القديمة بطرابلس", "طرابلس", "نسيج حضري تاريخي من أزقة وأسواق ومبانٍ قديمة في قلب طرابلس.", aliases=("Old City Tripoli",), architecture={"style": "historic Mediterranean and Ottoman-era urban fabric", "structures": ["narrow lanes", "courtyards", "historic facades"]}, environment={"crowd": "pedestrians and shopkeepers", "ground": "stone and paved lanes"}, visual={"detail": "historic North African urban realism"}, lighting={"day": "filtered sunlight", "night": "warm shop lighting"}, time="late afternoon", props=("wooden doors", "market signs", "shop awnings", "street carts")),
        _loc("loc-libya-tripoli-martyrs-square", "ميدان الشهداء", "طرابلس", "ساحة حضرية مفتوحة في وسط طرابلس تصلح لمشاهد المدينة والتجمعات والحركة اليومية.", aliases=("Martyrs' Square",), architecture={"style": "modern civic square", "structures": ["open plaza", "surrounding civic buildings"]}, environment={"crowd": "pedestrians", "traffic": "urban traffic"}, visual={"detail": "contemporary Tripoli city realism"}, lighting={"day": "bright coastal daylight", "night": "city practical lights"}, time="evening", props=("cars", "streetlights", "paving", "signage")),
        _loc("loc-libya-tripoli-corniche", "كورنيش طرابلس", "طرابلس", "واجهة بحرية متوسطية مناسبة للمشي والقيادة والغروب والمشاهد الاجتماعية.", aliases=("Tripoli Corniche",), geography={"coast": "Mediterranean Sea"}, environment={"water": "Mediterranean Sea", "traffic": "coastal road", "crowd": "walkers"}, visual={"detail": "Mediterranean coastal realism"}, lighting={"sunset": "warm sea horizon", "night": "coastal street lights"}, time="sunset", props=("cars", "pedestrians", "sea horizon", "streetlights")),
        _loc("loc-libya-tripoli-radisson-area", "منطقة فندقية ساحلية بطرابلس - موقع عام", "طرابلس", "موقع عام غير منسوب لفندق محدد، يمثل منطقة فندقية ساحلية حديثة للمشاهد المعاصرة.", architecture={"style": "modern coastal hospitality district"}, environment={"crowd": "travelers and staff", "vegetation": "ornamental landscaping"}, visual={"detail": "modern Libyan urban realism"}, lighting={"day": "soft coastal daylight", "night": "hotel and street practicals"}, props=("luggage", "cars", "palms"), negative=("do not reproduce a specific hotel brand or logo",)),
        _loc("loc-libya-leptis-magna", "لبدة الكبرى", "الخمس", "موقع أثري روماني ساحلي واسع يمكن استخدامه للمغامرة والتاريخ والغموض.", aliases=("Leptis Magna",), architecture={"era": "Roman", "structures": ["columns", "forum", "arches", "theatre"]}, environment={"terrain": "archaeological coastal plain", "ground": "stone and sand"}, visual={"detail": "archaeological cinematic realism"}, lighting={"day": "strong Mediterranean sun", "sunset": "warm stone light"}, time="sunset", props=("stone columns", "ruins", "sand", "archaeological markers")),
        _loc("loc-libya-sabratha", "صبراتة", "صبراتة", "موقع أثري ساحلي معروف بآثاره الرومانية ومسرحه القديم.", aliases=("Sabratha",), architecture={"era": "Roman", "structures": ["ancient theatre", "columns", "temple ruins"]}, environment={"water": "Mediterranean coast", "terrain": "archaeological ruins"}, visual={"detail": "coastal archaeological realism"}, lighting={"day": "natural sun", "sunset": "warm ruins light"}, time="late afternoon", props=("stone ruins", "columns", "sea horizon")),
        _loc("loc-libya-benghazi-city", "وسط بنغازي - موقع حضري عام", "بنغازي", "بيئة حضرية ليبية عامة للمشاهد المعاصرة دون تمثيل مبنى محدد.", aliases=("Benghazi city",), architecture={"style": "mixed contemporary Mediterranean urban fabric"}, environment={"crowd": "local pedestrians", "traffic": "cars and taxis"}, visual={"detail": "grounded Libyan city realism"}, lighting={"day": "Mediterranean daylight", "night": "storefront practicals"}, time="day", props=("cars", "shops", "street signs")),
        _loc("loc-libya-gharyan-mountains", "مرتفعات غريان", "غريان", "بيئة جبلية في شمال غرب ليبيا مناسبة للمطاردات والرحلات والمشاهد الريفية.", aliases=("Gharyan",), environment={"terrain": "Jebel Nafusa highlands", "vegetation": "sparse Mediterranean vegetation"}, visual={"detail": "natural mountain realism"}, lighting={"sunrise": "soft warm light", "sunset": "golden ridge light"}, time="sunrise", props=("mountain roads", "stone buildings", "utility vehicles")),
        _loc("loc-libya-sahara-road", "طريق صحراوي في فزان", "فزان", "بيئة صحراوية عامة في جنوب ليبيا للمغامرة والسفر دون نسبتها إلى موقع أثري محدد.", geography={"region": "Fezzan"}, environment={"terrain": "Sahara desert", "vegetation": "sparse", "visibility": "long open horizons"}, visual={"detail": "realistic Sahara travel cinematography"}, lighting={"day": "hard desert sun", "sunset": "orange horizon"}, time="sunset", props=("4x4 vehicle", "water containers", "navigation equipment"), negative=("no fictional dunes presented as a named landmark",)),
        _loc("loc-libya-oasis-gat", "واحة غات - بيئة عامة", "غات", "بيئة واحة صحراوية عامة تصلح للسفر والمغامرة والمشاهد الاجتماعية المحلية.", aliases=("Ghat oasis",), environment={"terrain": "oasis and desert", "vegetation": "date palms", "water": "oasis water source"}, visual={"detail": "grounded oasis realism"}, lighting={"day": "bright desert light", "sunset": "warm palm silhouettes"}, time="late afternoon", props=("date palms", "water containers", "off-road vehicle")),
        _loc("loc-libya-local-cafe", "مقهى ليبي شعبي - موقع خيالي", "طرابلس", "مقهى خيالي مستوحى من المقاهي المحلية، مناسب للحوار والكوميديا والدراما.", architecture={"style": "fictional contemporary Libyan cafe", "structures": ["open storefront", "simple seating"]}, environment={"crowd": "local customers"}, visual={"detail": "warm social realism"}, lighting={"day": "ambient street light", "night": "warm cafe lamps"}, time="night", props=("tea glasses", "coffee cups", "tables", "chairs", "dominoes"), negative=("no real business branding",)),
    ]


def _char(
    id: str,
    name: str,
    description: str,
    *,
    personality: str,
    appearance: str,
    voice: str,
    speaking_style: str,
    visual_style: str,
    behavior_rules: tuple[str, ...],
) -> CharacterProfile:
    now = _now()
    return CharacterProfile(
        id=id,
        project_id=LIBRARY_PROJECT_ID,
        name=name,
        description=description,
        personality=personality,
        appearance=appearance,
        voice=voice,
        speaking_style=speaking_style,
        visual_style=visual_style,
        behavior_rules=behavior_rules,
        reference_asset_ids=(),
        provider_character_id=None,
        metadata={"library": "libya", "dialect": "ar-LY", "ready": True},
        version=1,
        created_at=now,
        updated_at=now,
    )


def characters() -> list[CharacterProfile]:
    return [
        _char("char-libya-ahmed", "أحمد", "شاب ليبي فضولي يعمل في مجال تقني ويحب حل المشكلات.", personality="فضولي وعملي وهادئ تحت الضغط", appearance="شاب ليبي بملابس مدنية معاصرة دون علامات تجارية", voice="male warm conversational", speaking_style="Libyan Arabic, natural short sentences", visual_style="grounded cinematic realism", behavior_rules=("لا يغيّر مظهره أو عمره بين المشاهد", "يتحقق من التفاصيل قبل اتخاذ قرار مهم")),
        _char("char-libya-salma", "سلمى", "صحفية ليبية خيالية تتابع القصص المحلية وتطرح أسئلة مباشرة.", personality="ذكية ومثابرة وحذرة", appearance="امرأة ليبية شابة بملابس مدنية عملية محتشمة", voice="female clear conversational", speaking_style="Libyan Arabic, concise investigative dialogue", visual_style="grounded documentary realism", behavior_rules=("تحافظ على نفس الملامح والملابس الأساسية في الحلقة", "لا تقدم إشاعة كحقيقة")),
        _char("char-libya-mabrouk", "مبروك", "سائق أجرة ليبي خيالي يعرف طرق المدينة ويضفي لمسة كوميدية.", personality="اجتماعي وسريع البديهة وكثير التعليق", appearance="رجل ليبي في منتصف العمر بملابس سائق بسيطة", voice="male expressive", speaking_style="Libyan Arabic, colloquial humorous rhythm", visual_style="naturalistic comedy realism", behavior_rules=("لا يقود بطريقة مستحيلة", "لا يختلق معلومات محلية على أنها مؤكدة")),
        _char("char-libya-nadia", "نادية", "طبيبة ليبية خيالية تتعامل مع الأزمات بهدوء.", personality="رحيمة ومنظمة وحازمة", appearance="طبيبة ليبية بملابس مهنية عامة بلا شعار مستشفى حقيقي", voice="female calm", speaking_style="Libyan Arabic with clear professional terminology", visual_style="grounded drama realism", behavior_rules=("تحافظ على هويتها المهنية", "لا تُنسب إليها مؤسسة طبية حقيقية دون طلب")),
        _char("char-libya-younes", "يونس", "مرشد رحلات ليبي خيالي يعرف الطرق الصحراوية ويهتم بالسلامة.", personality="صبور ومغامر وحذر", appearance="رجل ليبي بملابس سفر عملية مناسبة للبيئة الصحراوية", voice="male steady", speaking_style="Libyan Arabic, descriptive travel dialogue", visual_style="cinematic adventure realism", behavior_rules=("يحمل الماء ومعدات الملاحة في الرحلات الطويلة", "لا يقدم موقعاً خيالياً كمعلم حقيقي")),
        _char("char-libya-huda", "هدى", "معلمة ليبية خيالية تهتم بالأطفال وتدير المواقف اليومية بحكمة.", personality="صبورة ومرحة ومسؤولة", appearance="امرأة ليبية بملابس مدنية مهنية محتشمة", voice="female warm", speaking_style="Libyan Arabic, friendly family dialogue", visual_style="warm family realism", behavior_rules=("تحافظ على نبرة مناسبة للأطفال", "تتجنب التنميط الثقافي")),
        _char("char-libya-faraj", "فرج", "ميكانيكي ليبي خيالي يعمل في ورشة صغيرة ويحل مشاكل المركبات.", personality="عملي ومرح ومحب للتجربة", appearance="رجل ليبي بملابس ورشة عملية وآثار عمل خفيفة", voice="male rough friendly", speaking_style="Libyan Arabic, practical workshop language", visual_style="industrial cinematic realism", behavior_rules=("يحافظ على أدوات الورشة الأساسية", "لا يجعل المركبات تصلح فوراً بلا سبب")),
        _char("char-libya-rania", "رانيا", "مصورّة ليبية خيالية توثق الرحلات والأحداث المحلية.", personality="ملاحظة ودقيقة وفضولية", appearance="امرأة ليبية شابة تحمل كاميرا ومعدات تصوير بسيطة", voice="female energetic", speaking_style="Libyan Arabic, observational dialogue", visual_style="cinematic observational realism", behavior_rules=("تحافظ على معدات التصوير بين المشاهد", "لا تدعي توثيق حدث لم تره")),
    ]


def library_metadata() -> dict[str, Any]:
    return {
        "countryId": "libya",
        "libraryId": LIBRARY_PROJECT_ID,
        "version": LIBRARY_VERSION,
        "status": "partial",
        "dialects": ["ar-LY"],
        "categories": ["characters", "locations", "environments", "clothing", "dialects", "customs", "vehicles", "workplaces", "archetypes", "seriesTemplates", "relationships", "continuity", "storyFacts", "runningGags", "openThreads", "props", "visualRules", "audioRules"],
        "seriesTemplates": ["comedy-series", "action-series", "drama-series", "mystery-series", "adventure-series", "family-series"],
        "continuity": {"preserveCharacterIdentity": True, "preserveLocationIdentity": True, "preserveEstablishedFacts": True, "neverOverwriteUserChanges": True},
        "dialectRules": ["Use Libyan Arabic only when the selected language is Arabic and dialect is ar-LY.", "Do not fabricate a specific city dialect when it was not selected."],
        "customs": ["Represent local customs contextually and avoid treating one family's behavior as universal.", "Keep religious, social, and family details respectful and non-stereotyped."],
        "vehicles": ["sedan", "taxi", "pickup", "4x4", "minibus", "motorcycle"],
        "workplaces": ["cafe", "workshop", "clinic", "school", "newsroom", "small shop", "taxi stand"],
        "archetypes": ["taxi driver", "journalist", "doctor", "teacher", "mechanic", "guide", "photographer", "young problem-solver"],
        "visualRules": {"style": "grounded cinematic realism", "preserveGeography": True, "avoidCulturalStereotypes": True},
        "audioRules": {"dialogue": "natural Libyan Arabic when selected", "music": "contextual and non-stereotyped", "sfx": "realistic local environment"},
        "seedSource": ["libya curated starter pack"],
    }
