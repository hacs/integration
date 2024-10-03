"""Voice handler with Azure."""

from __future__ import annotations

from collections.abc import AsyncIterable
from datetime import datetime
from enum import Enum
import logging
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from aiohttp.hdrs import ACCEPT, AUTHORIZATION, CONTENT_TYPE, USER_AGENT
import attr

from . import cloud_api
from .utils import utc_from_timestamp, utcnow

if TYPE_CHECKING:
    from . import Cloud, _ClientT


_LOGGER = logging.getLogger(__name__)


class VoiceError(Exception):
    """General Voice error."""


class VoiceTokenError(VoiceError):
    """Error with token handling."""


class VoiceReturnError(VoiceError):
    """Backend error for voice."""


class Gender(str, Enum):
    """Gender Type for voices."""

    MALE = "male"
    FEMALE = "female"


class AudioOutput(str, Enum):
    """Gender Type for voices."""

    MP3 = "mp3"
    RAW = "raw"


# The first entry for each language is the default voice
TTS_VOICES = {
    "af-ZA": [
        "AdriNeural",
        "WillemNeural",
    ],
    "am-ET": [
        "MekdesNeural",
        "AmehaNeural",
    ],
    "ar-AE": [
        "FatimaNeural",
        "HamdanNeural",
    ],
    "ar-BH": [
        "LailaNeural",
        "AliNeural",
    ],
    "ar-DZ": [
        "AminaNeural",
        "IsmaelNeural",
    ],
    "ar-EG": [
        "SalmaNeural",
        "ShakirNeural",
    ],
    "ar-IQ": [
        "RanaNeural",
        "BasselNeural",
    ],
    "ar-JO": [
        "SanaNeural",
        "TaimNeural",
    ],
    "ar-KW": [
        "NouraNeural",
        "FahedNeural",
    ],
    "ar-LB": [
        "LaylaNeural",
        "RamiNeural",
    ],
    "ar-LY": [
        "ImanNeural",
        "OmarNeural",
    ],
    "ar-MA": [
        "MounaNeural",
        "JamalNeural",
    ],
    "ar-OM": [
        "AbdullahNeural",
        "AyshaNeural",
    ],
    "ar-QA": [
        "AmalNeural",
        "MoazNeural",
    ],
    "ar-SA": [
        "ZariyahNeural",
        "HamedNeural",
    ],
    "ar-SY": [
        "AmanyNeural",
        "LaithNeural",
    ],
    "ar-TN": [
        "ReemNeural",
        "HediNeural",
    ],
    "ar-YE": [
        "MaryamNeural",
        "SalehNeural",
    ],
    "az-AZ": [
        "BabekNeural",
        "BanuNeural",
    ],
    "bg-BG": [
        "KalinaNeural",
        "BorislavNeural",
    ],
    "bn-BD": [
        "NabanitaNeural",
        "PradeepNeural",
    ],
    "bn-IN": [
        "TanishaaNeural",
        "BashkarNeural",
    ],
    "bs-BA": [
        "GoranNeural",
        "VesnaNeural",
    ],
    "ca-ES": [
        "JoanaNeural",
        "AlbaNeural",
        "EnricNeural",
    ],
    "cs-CZ": [
        "VlastaNeural",
        "AntoninNeural",
    ],
    "cy-GB": [
        "NiaNeural",
        "AledNeural",
    ],
    "da-DK": [
        "ChristelNeural",
        "JeppeNeural",
    ],
    "de-AT": [
        "IngridNeural",
        "JonasNeural",
    ],
    "de-CH": [
        "LeniNeural",
        "JanNeural",
    ],
    "de-DE": [
        "KatjaNeural",
        "AmalaNeural",
        "BerndNeural",
        "ChristophNeural",
        "ConradNeural",
        "ElkeNeural",
        "GiselaNeural",
        "KasperNeural",
        "KillianNeural",
        "KlarissaNeural",
        "KlausNeural",
        "LouisaNeural",
        "MajaNeural",
        "RalfNeural",
        "TanjaNeural",
    ],
    "el-GR": [
        "AthinaNeural",
        "NestorasNeural",
    ],
    "en-AU": [
        "NatashaNeural",
        "AnnetteNeural",
        "CarlyNeural",
        "DarrenNeural",
        "DuncanNeural",
        "ElsieNeural",
        "FreyaNeural",
        "JoanneNeural",
        "KenNeural",
        "KimNeural",
        "NeilNeural",
        "TimNeural",
        "TinaNeural",
        "WilliamNeural",
    ],
    "en-CA": [
        "ClaraNeural",
        "LiamNeural",
    ],
    "en-GB": [
        "LibbyNeural",
        "AbbiNeural",
        "AlfieNeural",
        "BellaNeural",
        "ElliotNeural",
        "EthanNeural",
        "HollieNeural",
        "MaisieNeural",
        "NoahNeural",
        "OliverNeural",
        "OliviaNeural",
        "RyanNeural",
        "SoniaNeural",
        "ThomasNeural",
    ],
    "en-HK": [
        "YanNeural",
        "SamNeural",
    ],
    "en-IE": [
        "EmilyNeural",
        "ConnorNeural",
    ],
    "en-IN": [
        "NeerjaNeural",
        "PrabhatNeural",
    ],
    "en-KE": [
        "AsiliaNeural",
        "ChilembaNeural",
    ],
    "en-NG": [
        "EzinneNeural",
        "AbeoNeural",
    ],
    "en-NZ": [
        "MollyNeural",
        "MitchellNeural",
    ],
    "en-PH": [
        "RosaNeural",
        "JamesNeural",
    ],
    "en-SG": [
        "LunaNeural",
        "WayneNeural",
    ],
    "en-TZ": [
        "ImaniNeural",
        "ElimuNeural",
    ],
    "en-US": [
        "JennyNeural",
        "AIGenerate1Neural",
        "AIGenerate2Neural",
        "AmberNeural",
        "AnaNeural",
        "AriaNeural",
        "AshleyNeural",
        "BrandonNeural",
        "ChristopherNeural",
        "CoraNeural",
        "DavisNeural",
        "ElizabethNeural",
        "EricNeural",
        "GuyNeural",
        "JacobNeural",
        "JaneNeural",
        "JasonNeural",
        "JennyMultilingualNeural",
        "MichelleNeural",
        "MonicaNeural",
        "NancyNeural",
        "RogerNeural",
        "SaraNeural",
        "SteffanNeural",
        "TonyNeural",
    ],
    "en-ZA": [
        "LeahNeural",
        "LukeNeural",
    ],
    "es-AR": [
        "ElenaNeural",
        "TomasNeural",
    ],
    "es-BO": [
        "SofiaNeural",
        "MarceloNeural",
    ],
    "es-CL": [
        "CatalinaNeural",
        "LorenzoNeural",
    ],
    "es-CO": [
        "SalomeNeural",
        "GonzaloNeural",
    ],
    "es-CR": [
        "MariaNeural",
        "JuanNeural",
    ],
    "es-CU": [
        "BelkysNeural",
        "ManuelNeural",
    ],
    "es-DO": [
        "RamonaNeural",
        "EmilioNeural",
    ],
    "es-EC": [
        "AndreaNeural",
        "LuisNeural",
    ],
    "es-ES": [
        "ElviraNeural",
        "AbrilNeural",
        "AlvaroNeural",
        "ArnauNeural",
        "DarioNeural",
        "EliasNeural",
        "EstrellaNeural",
        "IreneNeural",
        "LaiaNeural",
        "LiaNeural",
        "NilNeural",
        "SaulNeural",
        "TeoNeural",
        "TrianaNeural",
        "VeraNeural",
    ],
    "es-GQ": [
        "TeresaNeural",
        "JavierNeural",
    ],
    "es-GT": [
        "MartaNeural",
        "AndresNeural",
    ],
    "es-HN": [
        "KarlaNeural",
        "CarlosNeural",
    ],
    "es-MX": [
        "DaliaNeural",
        "BeatrizNeural",
        "CandelaNeural",
        "CarlotaNeural",
        "CecilioNeural",
        "GerardoNeural",
        "JorgeNeural",
        "LarissaNeural",
        "LibertoNeural",
        "LucianoNeural",
        "MarinaNeural",
        "NuriaNeural",
        "PelayoNeural",
        "RenataNeural",
        "YagoNeural",
    ],
    "es-NI": [
        "YolandaNeural",
        "FedericoNeural",
    ],
    "es-PA": [
        "MargaritaNeural",
        "RobertoNeural",
    ],
    "es-PE": [
        "CamilaNeural",
        "AlexNeural",
    ],
    "es-PR": [
        "KarinaNeural",
        "VictorNeural",
    ],
    "es-PY": [
        "TaniaNeural",
        "MarioNeural",
    ],
    "es-SV": [
        "LorenaNeural",
        "RodrigoNeural",
    ],
    "es-US": [
        "PalomaNeural",
        "AlonsoNeural",
    ],
    "es-UY": [
        "ValentinaNeural",
        "MateoNeural",
    ],
    "es-VE": [
        "PaolaNeural",
        "SebastianNeural",
    ],
    "et-EE": [
        "AnuNeural",
        "KertNeural",
    ],
    "eu-ES": [
        "AinhoaNeural",
        "AnderNeural",
    ],
    "fa-IR": [
        "DilaraNeural",
        "FaridNeural",
    ],
    "fi-FI": [
        "SelmaNeural",
        "HarriNeural",
        "NooraNeural",
    ],
    "fil-PH": [
        "BlessicaNeural",
        "AngeloNeural",
    ],
    "fr-BE": [
        "CharlineNeural",
        "GerardNeural",
    ],
    "fr-CA": [
        "SylvieNeural",
        "AntoineNeural",
        "JeanNeural",
    ],
    "fr-CH": [
        "ArianeNeural",
        "FabriceNeural",
    ],
    "fr-FR": [
        "DeniseNeural",
        "AlainNeural",
        "BrigitteNeural",
        "CelesteNeural",
        "ClaudeNeural",
        "CoralieNeural",
        "EloiseNeural",
        "HenriNeural",
        "JacquelineNeural",
        "JeromeNeural",
        "JosephineNeural",
        "MauriceNeural",
        "YvesNeural",
        "YvetteNeural",
    ],
    "ga-IE": [
        "OrlaNeural",
        "ColmNeural",
    ],
    "gl-ES": [
        "SabelaNeural",
        "RoiNeural",
    ],
    "gu-IN": [
        "DhwaniNeural",
        "NiranjanNeural",
    ],
    "he-IL": [
        "HilaNeural",
        "AvriNeural",
    ],
    "hi-IN": [
        "SwaraNeural",
        "MadhurNeural",
    ],
    "hr-HR": [
        "GabrijelaNeural",
        "SreckoNeural",
    ],
    "hu-HU": [
        "NoemiNeural",
        "TamasNeural",
    ],
    "hy-AM": [
        "AnahitNeural",
        "HaykNeural",
    ],
    "id-ID": [
        "GadisNeural",
        "ArdiNeural",
    ],
    "is-IS": [
        "GudrunNeural",
        "GunnarNeural",
    ],
    "it-IT": [
        "ElsaNeural",
        "BenignoNeural",
        "CalimeroNeural",
        "CataldoNeural",
        "DiegoNeural",
        "FabiolaNeural",
        "FiammaNeural",
        "GianniNeural",
        "ImeldaNeural",
        "IrmaNeural",
        "IsabellaNeural",
        "LisandroNeural",
        "PalmiraNeural",
        "PierinaNeural",
        "RinaldoNeural",
    ],
    "ja-JP": [
        "NanamiNeural",
        "AoiNeural",
        "DaichiNeural",
        "KeitaNeural",
        "MayuNeural",
        "NaokiNeural",
        "ShioriNeural",
    ],
    "jv-ID": [
        "SitiNeural",
        "DimasNeural",
    ],
    "ka-GE": [
        "EkaNeural",
        "GiorgiNeural",
    ],
    "kk-KZ": [
        "AigulNeural",
        "DauletNeural",
    ],
    "km-KH": [
        "SreymomNeural",
        "PisethNeural",
    ],
    "kn-IN": [
        "SapnaNeural",
        "GaganNeural",
    ],
    "ko-KR": [
        "SunHiNeural",
        "BongJinNeural",
        "GookMinNeural",
        "InJoonNeural",
        "JiMinNeural",
        "SeoHyeonNeural",
        "SoonBokNeural",
        "YuJinNeural",
    ],
    "lo-LA": [
        "KeomanyNeural",
        "ChanthavongNeural",
    ],
    "lt-LT": [
        "OnaNeural",
        "LeonasNeural",
    ],
    "lv-LV": [
        "EveritaNeural",
        "NilsNeural",
    ],
    "mk-MK": [
        "MarijaNeural",
        "AleksandarNeural",
    ],
    "ml-IN": [
        "SobhanaNeural",
        "MidhunNeural",
    ],
    "mn-MN": [
        "BataaNeural",
        "YesuiNeural",
    ],
    "mr-IN": [
        "AarohiNeural",
        "ManoharNeural",
    ],
    "ms-MY": [
        "YasminNeural",
        "OsmanNeural",
    ],
    "mt-MT": [
        "GraceNeural",
        "JosephNeural",
    ],
    "my-MM": [
        "NilarNeural",
        "ThihaNeural",
    ],
    "nb-NO": [
        "IselinNeural",
        "FinnNeural",
        "PernilleNeural",
    ],
    "ne-NP": [
        "HemkalaNeural",
        "SagarNeural",
    ],
    "nl-BE": [
        "DenaNeural",
        "ArnaudNeural",
    ],
    "nl-NL": [
        "ColetteNeural",
        "FennaNeural",
        "MaartenNeural",
    ],
    "pl-PL": [
        "AgnieszkaNeural",
        "MarekNeural",
        "ZofiaNeural",
    ],
    "ps-AF": [
        "LatifaNeural",
        "GulNawazNeural",
    ],
    "pt-BR": [
        "FranciscaNeural",
        "AntonioNeural",
        "BrendaNeural",
        "DonatoNeural",
        "ElzaNeural",
        "FabioNeural",
        "GiovannaNeural",
        "HumbertoNeural",
        "JulioNeural",
        "LeilaNeural",
        "LeticiaNeural",
        "ManuelaNeural",
        "NicolauNeural",
        "ValerioNeural",
        "YaraNeural",
    ],
    "pt-PT": [
        "RaquelNeural",
        "DuarteNeural",
        "FernandaNeural",
    ],
    "ro-RO": [
        "AlinaNeural",
        "EmilNeural",
    ],
    "ru-RU": [
        "SvetlanaNeural",
        "DariyaNeural",
        "DmitryNeural",
    ],
    "si-LK": [
        "ThiliniNeural",
        "SameeraNeural",
    ],
    "sk-SK": [
        "ViktoriaNeural",
        "LukasNeural",
    ],
    "sl-SI": [
        "PetraNeural",
        "RokNeural",
    ],
    "so-SO": [
        "UbaxNeural",
        "MuuseNeural",
    ],
    "sq-AL": [
        "AnilaNeural",
        "IlirNeural",
    ],
    "sr-RS": [
        "SophieNeural",
        "NicholasNeural",
    ],
    "su-ID": [
        "TutiNeural",
        "JajangNeural",
    ],
    "sv-SE": [
        "SofieNeural",
        "HilleviNeural",
        "MattiasNeural",
    ],
    "sw-KE": [
        "ZuriNeural",
        "RafikiNeural",
    ],
    "sw-TZ": [
        "RehemaNeural",
        "DaudiNeural",
    ],
    "ta-IN": [
        "PallaviNeural",
        "ValluvarNeural",
    ],
    "ta-LK": [
        "SaranyaNeural",
        "KumarNeural",
    ],
    "ta-MY": [
        "KaniNeural",
        "SuryaNeural",
    ],
    "ta-SG": [
        "VenbaNeural",
        "AnbuNeural",
    ],
    "te-IN": [
        "ShrutiNeural",
        "MohanNeural",
    ],
    "th-TH": [
        "AcharaNeural",
        "NiwatNeural",
        "PremwadeeNeural",
    ],
    "tr-TR": [
        "EmelNeural",
        "AhmetNeural",
    ],
    "uk-UA": [
        "PolinaNeural",
        "OstapNeural",
    ],
    "ur-IN": [
        "GulNeural",
        "SalmanNeural",
    ],
    "ur-PK": [
        "UzmaNeural",
        "AsadNeural",
    ],
    "uz-UZ": [
        "MadinaNeural",
        "SardorNeural",
    ],
    "vi-VN": [
        "HoaiMyNeural",
        "NamMinhNeural",
    ],
    "wuu-CN": [
        "XiaotongNeural",
        "YunzheNeural",
    ],
    "yue-CN": [
        "XiaoMinNeural",
        "YunSongNeural",
    ],
    "zh-CN": [
        "XiaoxiaoNeural",
        "XiaochenNeural",
        "XiaohanNeural",
        "XiaomengNeural",
        "XiaomoNeural",
        "XiaoqiuNeural",
        "XiaoruiNeural",
        "XiaoshuangNeural",
        "XiaoxuanNeural",
        "XiaoyanNeural",
        "XiaoyiNeural",
        "XiaoyouNeural",
        "XiaozhenNeural",
        "YunfengNeural",
        "YunhaoNeural",
        "YunjianNeural",
        "YunxiaNeural",
        "YunxiNeural",
        "YunyangNeural",
        "YunyeNeural",
        "YunzeNeural",
    ],
    "zh-CN-henan": [
        "YundengNeural",
    ],
    "zh-CN-liaoning": [
        "XiaobeiNeural",
    ],
    "zh-CN-shaanxi": [
        "XiaoniNeural",
    ],
    "zh-CN-shandong": [
        "YunxiangNeural",
    ],
    "zh-CN-sichuan": [
        "YunxiNeural",
    ],
    "zh-HK": [
        "HiuMaanNeural",
        "HiuGaaiNeural",
        "WanLungNeural",
    ],
    "zh-TW": [
        "HsiaoChenNeural",
        "HsiaoYuNeural",
        "YunJheNeural",
    ],
    "zu-ZA": [
        "ThandoNeural",
        "ThembaNeural",
    ],
}


STT_LANGUAGES = [
    "af-ZA",
    "am-ET",
    "ar-AE",
    "ar-BH",
    "ar-DZ",
    "ar-EG",
    "ar-IL",
    "ar-IQ",
    "ar-JO",
    "ar-KW",
    "ar-LB",
    "ar-LY",
    "ar-MA",
    "ar-OM",
    "ar-PS",
    "ar-QA",
    "ar-SA",
    "ar-SY",
    "ar-TN",
    "ar-YE",
    "az-AZ",
    "bg-BG",
    "bn-IN",
    "bs-BA",
    "ca-ES",
    "cs-CZ",
    "cy-GB",
    "da-DK",
    "de-AT",
    "de-CH",
    "de-DE",
    "el-GR",
    "en-AU",
    "en-CA",
    "en-GB",
    "en-GH",
    "en-HK",
    "en-IE",
    "en-IN",
    "en-KE",
    "en-NG",
    "en-NZ",
    "en-PH",
    "en-SG",
    "en-TZ",
    "en-US",
    "en-ZA",
    "es-AR",
    "es-BO",
    "es-CL",
    "es-CO",
    "es-CR",
    "es-CU",
    "es-DO",
    "es-EC",
    "es-ES",
    "es-GQ",
    "es-GT",
    "es-HN",
    "es-MX",
    "es-NI",
    "es-PA",
    "es-PE",
    "es-PR",
    "es-PY",
    "es-SV",
    "es-US",
    "es-UY",
    "es-VE",
    "et-EE",
    "eu-ES",
    "fa-IR",
    "fi-FI",
    "fil-PH",
    "fr-BE",
    "fr-CA",
    "fr-CH",
    "fr-FR",
    "ga-IE",
    "gl-ES",
    "gu-IN",
    "he-IL",
    "hi-IN",
    "hr-HR",
    "hu-HU",
    "hy-AM",
    "id-ID",
    "is-IS",
    "it-CH",
    "it-IT",
    "ja-JP",
    "jv-ID",
    "ka-GE",
    "kk-KZ",
    "km-KH",
    "kn-IN",
    "ko-KR",
    "lo-LA",
    "lt-LT",
    "lv-LV",
    "mk-MK",
    "ml-IN",
    "mn-MN",
    "mr-IN",
    "ms-MY",
    "mt-MT",
    "my-MM",
    "nb-NO",
    "ne-NP",
    "nl-BE",
    "nl-NL",
    "pl-PL",
    "ps-AF",
    "pt-BR",
    "pt-PT",
    "ro-RO",
    "ru-RU",
    "si-LK",
    "sk-SK",
    "sl-SI",
    "so-SO",
    "sq-AL",
    "sr-RS",
    "sv-SE",
    "sw-KE",
    "sw-TZ",
    "ta-IN",
    "te-IN",
    "th-TH",
    "tr-TR",
    "uk-UA",
    "uz-UZ",
    "vi-VN",
    "wuu-CN",
    "yue-CN",
    "zh-CN",
    "zh-CN-shandong",
    "zh-CN-sichuan",
    "zh-HK",
    "zh-TW",
    "zu-ZA",
]

# Old. Do not update anymore.
MAP_VOICE = {
    ("af-ZA", Gender.FEMALE): "AdriNeural",
    ("af-ZA", Gender.MALE): "WillemNeural",
    ("am-ET", Gender.FEMALE): "MekdesNeural",
    ("am-ET", Gender.MALE): "AmehaNeural",
    ("ar-DZ", Gender.FEMALE): "AminaNeural",
    ("ar-DZ", Gender.MALE): "IsmaelNeural",
    ("ar-BH", Gender.FEMALE): "LailaNeural",
    ("ar-BH", Gender.MALE): "AliNeural",
    ("ar-EG", Gender.FEMALE): "SalmaNeural",
    ("ar-EG", Gender.MALE): "ShakirNeural",
    ("ar-IQ", Gender.FEMALE): "RanaNeural",
    ("ar-IQ", Gender.MALE): "BasselNeural",
    ("ar-JO", Gender.FEMALE): "SanaNeural",
    ("ar-JO", Gender.MALE): "TaimNeural",
    ("ar-KW", Gender.FEMALE): "NouraNeural",
    ("ar-KW", Gender.MALE): "FahedNeural",
    ("ar-LY", Gender.FEMALE): "ImanNeural",
    ("ar-LY", Gender.MALE): "OmarNeural",
    ("ar-MA", Gender.FEMALE): "MounaNeural",
    ("ar-MA", Gender.MALE): "JamalNeural",
    ("ar-QA", Gender.FEMALE): "AmalNeural",
    ("ar-QA", Gender.MALE): "MoazNeural",
    ("ar-SA", Gender.FEMALE): "ZariyahNeural",
    ("ar-SA", Gender.MALE): "HamedNeural",
    ("ar-SY", Gender.FEMALE): "AmanyNeural",
    ("ar-SY", Gender.MALE): "LaithNeural",
    ("ar-TN", Gender.FEMALE): "ReemNeural",
    ("ar-TN", Gender.MALE): "HediNeural",
    ("ar-AE", Gender.FEMALE): "FatimaNeural",
    ("ar-AE", Gender.MALE): "HamdanNeural",
    ("ar-YE", Gender.FEMALE): "MaryamNeural",
    ("ar-YE", Gender.MALE): "SalehNeural",
    ("bn-BD", Gender.FEMALE): "NabanitaNeural",
    ("bn-BD", Gender.MALE): "PradeepNeural",
    ("bn-IN", Gender.FEMALE): "TanishaaNeural",
    ("bn-IN", Gender.MALE): "BashkarNeural",
    ("bg-BG", Gender.FEMALE): "KalinaNeural",
    ("bg-BG", Gender.MALE): "BorislavNeural",
    ("my-MM", Gender.FEMALE): "NilarNeural",
    ("my-MM", Gender.MALE): "ThihaNeural",
    ("ca-ES", Gender.FEMALE): "JoanaNeural",
    ("ca-ES", Gender.MALE): "EnricNeural",
    ("zh-HK", Gender.FEMALE): "HiuMaanNeural",
    ("zh-HK", Gender.MALE): "WanLungNeural",
    ("zh-CN", Gender.FEMALE): "XiaoxiaoNeural",
    ("zh-CN", Gender.MALE): "YunyangNeural",
    ("zh-TW", Gender.FEMALE): "HsiaoChenNeural",
    ("zh-TW", Gender.MALE): "YunJheNeural",
    ("hr-HR", Gender.FEMALE): "GabrijelaNeural",
    ("hr-HR", Gender.MALE): "SreckoNeural",
    ("cs-CZ", Gender.FEMALE): "VlastaNeural",
    ("cs-CZ", Gender.MALE): "AntoninNeural",
    ("da-DK", Gender.FEMALE): "ChristelNeural",
    ("da-DK", Gender.MALE): "JeppeNeural",
    ("nl-BE", Gender.FEMALE): "DenaNeural",
    ("nl-BE", Gender.MALE): "ArnaudNeural",
    ("nl-NL", Gender.FEMALE): "ColetteNeural",
    ("nl-NL", Gender.MALE): "MaartenNeural",
    ("en-AU", Gender.FEMALE): "NatashaNeural",
    ("en-AU", Gender.MALE): "WilliamNeural",
    ("en-CA", Gender.FEMALE): "ClaraNeural",
    ("en-CA", Gender.MALE): "LiamNeural",
    ("en-HK", Gender.FEMALE): "YanNeural",
    ("en-HK", Gender.MALE): "SamNeural",
    ("en-IN", Gender.FEMALE): "NeerjaNeural",
    ("en-IN", Gender.MALE): "PrabhatNeural",
    ("en-IE", Gender.FEMALE): "EmilyNeural",
    ("en-IE", Gender.MALE): "ConnorNeural",
    ("en-KE", Gender.FEMALE): "AsiliaNeural",
    ("en-KE", Gender.MALE): "ChilembaNeural",
    ("en-NZ", Gender.FEMALE): "MollyNeural",
    ("en-NZ", Gender.MALE): "MitchellNeural",
    ("en-NG", Gender.FEMALE): "EzinneNeural",
    ("en-NG", Gender.MALE): "AbeoNeural",
    ("en-PH", Gender.FEMALE): "RosaNeural",
    ("en-PH", Gender.MALE): "JamesNeural",
    ("en-SG", Gender.FEMALE): "LunaNeural",
    ("en-SG", Gender.MALE): "WayneNeural",
    ("en-ZA", Gender.FEMALE): "LeahNeural",
    ("en-ZA", Gender.MALE): "LukeNeural",
    ("en-TZ", Gender.FEMALE): "ImaniNeural",
    ("en-TZ", Gender.MALE): "ElimuNeural",
    ("en-GB", Gender.FEMALE): "LibbyNeural",
    ("en-GB", Gender.MALE): "RyanNeural",
    ("en-US", Gender.FEMALE): "JennyNeural",
    ("en-US", Gender.MALE): "GuyNeural",
    ("et-EE", Gender.FEMALE): "AnuNeural",
    ("et-EE", Gender.MALE): "KertNeural",
    ("fil-PH", Gender.FEMALE): "BlessicaNeural",
    ("fil-PH", Gender.MALE): "AngeloNeural",
    ("fi-FI", Gender.FEMALE): "SelmaNeural",
    ("fi-FI", Gender.MALE): "HarriNeural",
    ("fr-BE", Gender.FEMALE): "CharlineNeural",
    ("fr-BE", Gender.MALE): "GerardNeural",
    ("fr-CA", Gender.FEMALE): "SylvieNeural",
    ("fr-CA", Gender.MALE): "AntoineNeural",
    ("fr-FR", Gender.FEMALE): "DeniseNeural",
    ("fr-FR", Gender.MALE): "HenriNeural",
    ("fr-CH", Gender.FEMALE): "ArianeNeural",
    ("fr-CH", Gender.MALE): "FabriceNeural",
    ("gl-ES", Gender.FEMALE): "SabelaNeural",
    ("gl-ES", Gender.MALE): "RoiNeural",
    ("de-AT", Gender.FEMALE): "IngridNeural",
    ("de-AT", Gender.MALE): "JonasNeural",
    ("de-DE", Gender.FEMALE): "KatjaNeural",
    ("de-DE", Gender.MALE): "ConradNeural",
    ("de-CH", Gender.FEMALE): "LeniNeural",
    ("de-CH", Gender.MALE): "JanNeural",
    ("el-GR", Gender.FEMALE): "AthinaNeural",
    ("el-GR", Gender.MALE): "NestorasNeural",
    ("gu-IN", Gender.FEMALE): "DhwaniNeural",
    ("gu-IN", Gender.MALE): "NiranjanNeural",
    ("he-IL", Gender.FEMALE): "HilaNeural",
    ("he-IL", Gender.MALE): "AvriNeural",
    ("hi-IN", Gender.FEMALE): "SwaraNeural",
    ("hi-IN", Gender.MALE): "MadhurNeural",
    ("hu-HU", Gender.FEMALE): "NoemiNeural",
    ("hu-HU", Gender.MALE): "TamasNeural",
    ("is-IS", Gender.FEMALE): "GudrunNeural",
    ("is-IS", Gender.MALE): "GunnarNeural",
    ("id-ID", Gender.FEMALE): "GadisNeural",
    ("id-ID", Gender.MALE): "ArdiNeural",
    ("ga-IE", Gender.FEMALE): "OrlaNeural",
    ("ga-IE", Gender.MALE): "ColmNeural",
    ("it-IT", Gender.FEMALE): "ElsaNeural",
    ("it-IT", Gender.MALE): "DiegoNeural",
    ("ja-JP", Gender.FEMALE): "NanamiNeural",
    ("ja-JP", Gender.MALE): "KeitaNeural",
    ("jv-ID", Gender.FEMALE): "SitiNeural",
    ("jv-ID", Gender.MALE): "DimasNeural",
    ("kn-IN", Gender.FEMALE): "SapnaNeural",
    ("kn-IN", Gender.MALE): "GaganNeural",
    ("kk-KZ", Gender.FEMALE): "AigulNeural",
    ("kk-KZ", Gender.MALE): "DauletNeural",
    ("km-KH", Gender.FEMALE): "SreymomNeural",
    ("km-KH", Gender.MALE): "PisethNeural",
    ("ko-KR", Gender.FEMALE): "SunHiNeural",
    ("ko-KR", Gender.MALE): "InJoonNeural",
    ("lo-LA", Gender.FEMALE): "KeomanyNeural",
    ("lo-LA", Gender.MALE): "ChanthavongNeural",
    ("lv-LV", Gender.FEMALE): "EveritaNeural",
    ("lv-LV", Gender.MALE): "NilsNeural",
    ("lt-LT", Gender.FEMALE): "OnaNeural",
    ("lt-LT", Gender.MALE): "LeonasNeural",
    ("mk-MK", Gender.FEMALE): "MarijaNeural",
    ("mk-MK", Gender.MALE): "AleksandarNeural",
    ("ms-MY", Gender.FEMALE): "YasminNeural",
    ("ms-MY", Gender.MALE): "OsmanNeural",
    ("ml-IN", Gender.FEMALE): "SobhanaNeural",
    ("ml-IN", Gender.MALE): "MidhunNeural",
    ("mt-MT", Gender.FEMALE): "GraceNeural",
    ("mt-MT", Gender.MALE): "JosephNeural",
    ("mr-IN", Gender.FEMALE): "AarohiNeural",
    ("mr-IN", Gender.MALE): "ManoharNeural",
    ("nb-NO", Gender.FEMALE): "IselinNeural",
    ("nb-NO", Gender.MALE): "FinnNeural",
    ("ps-AF", Gender.FEMALE): "LatifaNeural",
    ("ps-AF", Gender.MALE): "GulNawazNeural",
    ("fa-IR", Gender.FEMALE): "DilaraNeural",
    ("fa-IR", Gender.MALE): "FaridNeural",
    ("pl-PL", Gender.FEMALE): "AgnieszkaNeural",
    ("pl-PL", Gender.MALE): "MarekNeural",
    ("pt-BR", Gender.FEMALE): "FranciscaNeural",
    ("pt-BR", Gender.MALE): "AntonioNeural",
    ("pt-PT", Gender.FEMALE): "RaquelNeural",
    ("pt-PT", Gender.MALE): "DuarteNeural",
    ("ro-RO", Gender.FEMALE): "AlinaNeural",
    ("ro-RO", Gender.MALE): "EmilNeural",
    ("ru-RU", Gender.FEMALE): "SvetlanaNeural",
    ("ru-RU", Gender.MALE): "DmitryNeural",
    ("sr-RS", Gender.FEMALE): "SophieNeural",
    ("sr-RS", Gender.MALE): "NicholasNeural",
    ("si-LK", Gender.FEMALE): "ThiliniNeural",
    ("si-LK", Gender.MALE): "SameeraNeural",
    ("sk-SK", Gender.FEMALE): "ViktoriaNeural",
    ("sk-SK", Gender.MALE): "LukasNeural",
    ("sl-SI", Gender.FEMALE): "PetraNeural",
    ("sl-SI", Gender.MALE): "RokNeural",
    ("so-SO", Gender.FEMALE): "UbaxNeural",
    ("so-SO", Gender.MALE): "MuuseNeural",
    ("es-AR", Gender.FEMALE): "ElenaNeural",
    ("es-AR", Gender.MALE): "TomasNeural",
    ("es-BO", Gender.FEMALE): "SofiaNeural",
    ("es-BO", Gender.MALE): "MarceloNeural",
    ("es-CL", Gender.FEMALE): "CatalinaNeural",
    ("es-CL", Gender.MALE): "LorenzoNeural",
    ("es-CO", Gender.FEMALE): "SalomeNeural",
    ("es-CO", Gender.MALE): "GonzaloNeural",
    ("es-CR", Gender.FEMALE): "MariaNeural",
    ("es-CR", Gender.MALE): "JuanNeural",
    ("es-CU", Gender.FEMALE): "BelkysNeural",
    ("es-CU", Gender.MALE): "ManuelNeural",
    ("es-DO", Gender.FEMALE): "RamonaNeural",
    ("es-DO", Gender.MALE): "EmilioNeural",
    ("es-EC", Gender.FEMALE): "AndreaNeural",
    ("es-EC", Gender.MALE): "LuisNeural",
    ("es-SV", Gender.FEMALE): "LorenaNeural",
    ("es-SV", Gender.MALE): "RodrigoNeural",
    ("es-GQ", Gender.FEMALE): "TeresaNeural",
    ("es-GQ", Gender.MALE): "JavierNeural",
    ("es-GT", Gender.FEMALE): "MartaNeural",
    ("es-GT", Gender.MALE): "AndresNeural",
    ("es-HN", Gender.FEMALE): "KarlaNeural",
    ("es-HN", Gender.MALE): "CarlosNeural",
    ("es-MX", Gender.FEMALE): "DaliaNeural",
    ("es-MX", Gender.MALE): "JorgeNeural",
    ("es-NI", Gender.FEMALE): "YolandaNeural",
    ("es-NI", Gender.MALE): "FedericoNeural",
    ("es-PA", Gender.FEMALE): "MargaritaNeural",
    ("es-PA", Gender.MALE): "RobertoNeural",
    ("es-PY", Gender.FEMALE): "TaniaNeural",
    ("es-PY", Gender.MALE): "MarioNeural",
    ("es-PE", Gender.FEMALE): "CamilaNeural",
    ("es-PE", Gender.MALE): "AlexNeural",
    ("es-PR", Gender.FEMALE): "KarinaNeural",
    ("es-PR", Gender.MALE): "VictorNeural",
    ("es-ES", Gender.FEMALE): "ElviraNeural",
    ("es-ES", Gender.MALE): "AlvaroNeural",
    ("es-UY", Gender.FEMALE): "ValentinaNeural",
    ("es-UY", Gender.MALE): "MateoNeural",
    ("es-US", Gender.FEMALE): "PalomaNeural",
    ("es-US", Gender.MALE): "AlonsoNeural",
    ("es-VE", Gender.FEMALE): "PaolaNeural",
    ("es-VE", Gender.MALE): "SebastianNeural",
    ("su-ID", Gender.FEMALE): "TutiNeural",
    ("su-ID", Gender.MALE): "JajangNeural",
    ("sw-KE", Gender.FEMALE): "ZuriNeural",
    ("sw-KE", Gender.MALE): "RafikiNeural",
    ("sw-TZ", Gender.FEMALE): "RehemaNeural",
    ("sw-TZ", Gender.MALE): "DaudiNeural",
    ("sv-SE", Gender.FEMALE): "SofieNeural",
    ("sv-SE", Gender.MALE): "MattiasNeural",
    ("ta-IN", Gender.FEMALE): "PallaviNeural",
    ("ta-IN", Gender.MALE): "ValluvarNeural",
    ("ta-SG", Gender.FEMALE): "VenbaNeural",
    ("ta-SG", Gender.MALE): "AnbuNeural",
    ("ta-LK", Gender.FEMALE): "SaranyaNeural",
    ("ta-LK", Gender.MALE): "KumarNeural",
    ("te-IN", Gender.FEMALE): "ShrutiNeural",
    ("te-IN", Gender.MALE): "MohanNeural",
    ("th-TH", Gender.FEMALE): "AcharaNeural",
    ("th-TH", Gender.MALE): "NiwatNeural",
    ("tr-TR", Gender.FEMALE): "EmelNeural",
    ("tr-TR", Gender.MALE): "AhmetNeural",
    ("uk-UA", Gender.FEMALE): "PolinaNeural",
    ("uk-UA", Gender.MALE): "OstapNeural",
    ("ur-IN", Gender.FEMALE): "GulNeural",
    ("ur-IN", Gender.MALE): "SalmanNeural",
    ("ur-PK", Gender.FEMALE): "UzmaNeural",
    ("ur-PK", Gender.MALE): "AsadNeural",
    ("uz-UZ", Gender.FEMALE): "MadinaNeural",
    ("uz-UZ", Gender.MALE): "SardorNeural",
    ("vi-VN", Gender.FEMALE): "HoaiMyNeural",
    ("vi-VN", Gender.MALE): "NamMinhNeural",
    ("cy-GB", Gender.FEMALE): "NiaNeural",
    ("cy-GB", Gender.MALE): "AledNeural",
    ("zu-ZA", Gender.FEMALE): "ThandoNeural",
    ("zu-ZA", Gender.MALE): "ThembaNeural",
}


@attr.s
class STTResponse:
    """Response of STT."""

    success: bool = attr.ib()
    text: str | None = attr.ib()


class Voice:
    """Class to help manage azure STT and TTS."""

    def __init__(self, cloud: Cloud[_ClientT]) -> None:
        """Initialize azure voice."""
        self.cloud = cloud
        self._token: str | None = None
        self._endpoint_tts: str | None = None
        self._endpoint_stt: str | None = None
        self._valid: datetime | None = None

    def _validate_token(self) -> bool:
        """Validate token outside of coroutine."""
        if self._valid and utcnow() < self._valid:
            return True
        return False

    async def _update_token(self) -> None:
        """Update token details."""
        resp = await cloud_api.async_voice_connection_details(self.cloud)
        if resp.status != 200:
            raise VoiceTokenError

        data = await resp.json()
        self._token = data["authorized_key"]
        self._endpoint_stt = data["endpoint_stt"]
        self._endpoint_tts = data["endpoint_tts"]
        self._valid = utc_from_timestamp(float(data["valid"]))

    async def process_stt(
        self,
        *,
        stream: AsyncIterable[bytes],
        content_type: str,
        language: str,
        force_token_renewal: bool = False,
    ) -> STTResponse:
        """Stream Audio to Azure cognitive instance."""
        if language not in STT_LANGUAGES:
            raise VoiceError(f"Language {language} not supported")

        if force_token_renewal or not self._validate_token():
            await self._update_token()

        # Send request
        async with self.cloud.websession.post(
            f"{self._endpoint_stt}?language={language}&profanity=raw",
            headers={
                CONTENT_TYPE: content_type,
                AUTHORIZATION: f"Bearer {self._token}",
                ACCEPT: "application/json;text/xml",
                USER_AGENT: self.cloud.client.client_name,
            },
            data=stream,
            expect100=True,
            chunked=True,
        ) as resp:
            if resp.status == 429 and not force_token_renewal:
                # By checking the force_token_renewal argument, we limit retries to 1.
                _LOGGER.info("Retrying with new token")
                return await self.process_stt(
                    stream=stream,
                    content_type=content_type,
                    language=language,
                    force_token_renewal=True,
                )
            if resp.status not in (200, 201):
                raise VoiceReturnError(
                    f"Error processing {language} speech: "
                    f"{resp.status} {await resp.text()}",
                )
            data = await resp.json()

        # Parse Answer
        return STTResponse(
            data["RecognitionStatus"] == "Success",
            data.get("DisplayText"),
        )

    async def process_tts(
        self,
        *,
        text: str,
        language: str,
        output: AudioOutput,
        voice: str | None = None,
        gender: Gender | None = None,
        force_token_renewal: bool = False,
    ) -> bytes:
        """Get Speech from text over Azure."""
        if language not in TTS_VOICES:
            raise VoiceError(f"Unsupported language {language}")

        # Backwards compatibility for old config
        if voice is None and gender is not None:
            voice = MAP_VOICE.get((language, gender))

        # If no voice picked, pick first one.
        if voice is None:
            voice = TTS_VOICES[language][0]

        if voice not in TTS_VOICES[language]:
            raise VoiceError(f"Unsupported voice {voice} for language {language}")

        if force_token_renewal or not self._validate_token():
            await self._update_token()

        # SSML
        xml_body = ElementTree.Element("speak", version="1.0")
        xml_body.set("{http://www.w3.org/XML/1998/namespace}lang", language)
        voice_el = ElementTree.SubElement(xml_body, "voice")
        voice_el.set("{http://www.w3.org/XML/1998/namespace}lang", language)
        voice_el.set(
            "name",
            f"Microsoft Server Speech Text to Speech Voice ({language}, {voice})",
        )
        voice_el.text = text[:2048]

        # We can not get here without this being set, but mypy does not know that.
        assert self._endpoint_tts is not None

        if output == AudioOutput.RAW:
            output_header = "raw-16khz-16bit-mono-pcm"
        else:
            output_header = "audio-24khz-48kbitrate-mono-mp3"

        # Send request
        async with self.cloud.websession.post(
            self._endpoint_tts,
            headers={
                CONTENT_TYPE: "application/ssml+xml",
                AUTHORIZATION: f"Bearer {self._token}",
                "X-Microsoft-OutputFormat": output_header,
                USER_AGENT: self.cloud.client.client_name,
            },
            data=ElementTree.tostring(xml_body),
        ) as resp:
            if resp.status == 429 and not force_token_renewal:
                # By checking the force_token_renewal argument, we limit retries to 1.
                _LOGGER.info("Retrying with new token")
                return await self.process_tts(
                    text=text,
                    language=language,
                    output=output,
                    voice=voice,
                    gender=gender,
                    force_token_renewal=True,
                )
            if resp.status not in (200, 201):
                raise VoiceReturnError(
                    f"Error receiving TTS with {language}/{voice}: "
                    f"{resp.status} {await resp.text()}",
                )
            return await resp.read()
