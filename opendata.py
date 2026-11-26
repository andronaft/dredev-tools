"""The open datasets published on Zenodo (26 November 2026) and their schema.org markup.

The DOIs tie the site's Dataset markup to the Zenodo records, so Google Dataset Search treats them as one dataset.
GWP_LD and AWG_LD are copied from experimental/open-data (schema-org-dataset.jsonld, built by its build.py); the
refrigerant-pt and NEC pages build their own Dataset and only add the DOI here.
SHIFT_PATTERNS_LD and HOLIDAYS_REST_LD (the shift pages) are copied the same way but not published yet: their DOI is
"" until the session that owns open-data publishes them, and with_doi() adds the DOI and downloads once it is set.
"""

DOI = {
    "refrigerant-pt": "10.5281/zenodo.24545607",
    "nec-edition-by-state": "10.5281/zenodo.24545613",
    "refrigerant-gwp-safety": "10.5281/zenodo.24545617",
    "awg-to-mm2": "10.5281/zenodo.24545621",
    # Not published yet: the session that owns open-data fills these in after Zenodo publishes them.
    "shift-rota-patterns": "10.5281/zenodo.24547071",
    "public-holidays-rest-rules": "10.5281/zenodo.24547077",
    "aquarium-ammonia-fraction": "10.5281/zenodo.24547079",
    "seawater-salinity-specific-gravity": "10.5281/zenodo.24547081",
    "roof-pitch-multipliers": "10.5281/zenodo.24547073",
    "rebar-sizes-us-eu-canada": "10.5281/zenodo.24547083",
}
# The files of each dataset not built from a full copy below, in the order of the Zenodo record.
FILES = {
    "shift-rota-patterns": ["shift-rota-patterns.csv", "shift-rota-patterns.json"],
    "public-holidays-rest-rules": ["public-holidays-rest-rules.csv", "public-holidays.csv", "public-holidays-rest-rules.json"],
}


def doi_props(ds):
    """identifier + sameAs for a Dataset whose copy on Zenodo has this DOI; nothing while the DOI is not known yet."""
    doi = DOI[ds]
    if not doi:
        return {}
    return {"identifier": [f"https://doi.org/{doi}", f"doi:{doi}"], "sameAs": [f"https://doi.org/{doi}"]}


def with_doi(ld, ds):
    """A Dataset dict from open-data (schema-org-dataset.jsonld without its mirrors) plus the DOI and the Zenodo
    downloads once the record exists. Before that the page carries the Dataset without them."""
    out = dict(ld, **doi_props(ds))
    if DOI[ds]:
        record = DOI[ds].rsplit(".", 1)[1]
        out["distribution"] = [{"@type": "DataDownload", "encodingFormat": "text/csv" if f.endswith(".csv") else "application/json",
                                "contentUrl": f"https://zenodo.org/records/{record}/files/{f}?download=1"} for f in FILES[ds]]
        out["citation"] = out["citation"].rsplit(". https://", 1)[0] + f". https://doi.org/{DOI[ds]}"
    return out


GWP_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/hvac/pt-chart/#gwp-dataset",
    "name": "Global warming potential, ozone depletion potential and ASHRAE safety class of 22 refrigerants, as listed by US EPA",
    "alternateName": "Refrigerant GWP, ODP and safety class (US EPA)",
    "description": "One row per refrigerant for the 22 refrigerants in the Dre Dev PT tables: the 100-year global warming potential exactly as US EPA prints it (with the basis EPA states: AR4, WMO 2022 or the SNAP list), the ozone depletion potential where there is one, and the ASHRAE Standard 34 safety class, each with the EPA page it was read on (read 12 November 2026). One publisher for every GWP, so values can be compared; makers' literature can differ by a unit or two. Companion to the refrigerant PT tables dataset.",
    "url": "https://zhukovskyi.space/calculators/hvac/pt-chart/",
    "version": "1.0.0",
    "datePublished": "2026-11-25",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "refrigerant",
        "GWP",
        "global warming potential",
        "ozone depletion potential",
        "ASHRAE 34",
        "safety class",
        "A2L",
        "AIM Act",
        "HFC",
        "US EPA"
    ],
    "citation": "Zhukovskyi, A. (2026). Global warming potential, ozone depletion potential and ASHRAE safety class of 22 refrigerants, as listed by US EPA (Version 1.0.0) [Data set]. Dre Dev. https://doi.org/10.5281/zenodo.24545617",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "refrigerant",
            "description": "ASHRAE designation, for example R-454B."
        },
        {
            "@type": "PropertyValue",
            "name": "gwp_100yr",
            "description": "100-year global warming potential as printed by US EPA.",
            "unitText": "dimensionless (CO2 = 1)"
        },
        {
            "@type": "PropertyValue",
            "name": "gwp_basis",
            "description": "The basis EPA states for the value: IPCC 2007 (AR4), AR4 calculated for the blend, WMO 2022, or SNAP list."
        },
        {
            "@type": "PropertyValue",
            "name": "gwp_source",
            "description": "The EPA page the GWP was read on."
        },
        {
            "@type": "PropertyValue",
            "name": "odp",
            "description": "Ozone depletion potential; 0 where EPA lists none.",
            "unitText": "dimensionless (CFC-11 = 1)"
        },
        {
            "@type": "PropertyValue",
            "name": "odp_source",
            "description": "The EPA page the ODP was read on; empty when odp is 0."
        },
        {
            "@type": "PropertyValue",
            "name": "safety_class",
            "description": "ASHRAE Standard 34 safety class (A1, A2L, A3, B2L)."
        },
        {
            "@type": "PropertyValue",
            "name": "safety_class_source",
            "description": "EPA SNAP page that prints the same class; empty for R-717 (EPA prints B2) and R-12 (not on the SNAP pages read)."
        }
    ],
    "distribution": [
        {
            "@type": "DataDownload",
            "encodingFormat": "text/csv",
            "contentUrl": "https://zenodo.org/records/24545617/files/refrigerant-gwp-safety.csv?download=1"
        },
        {
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": "https://zenodo.org/records/24545617/files/refrigerant-gwp-safety.json?download=1"
        }
    ],
    "sameAs": [
        "https://doi.org/10.5281/zenodo.24545617"
    ],
    "isBasedOn": [
        "https://www.epa.gov/climate-hfcs-reduction/technology-transitions-gwp-reference-table",
        "https://www.epa.gov/ozone-layer-protection/ozone-depleting-substances",
        "https://www.epa.gov/snap/substitutes-residential-and-light-commercial-air-conditioning-and-heat-pumps"
    ],
    "identifier": [
        "https://doi.org/10.5281/zenodo.24545617",
        "doi:10.5281/zenodo.24545617"
    ]
}

AWG_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/electrical/awg-to-mm2.html#dataset",
    "name": "AWG and kcmil wire sizes in mm², circular mils, diameter, nearest IEC 60228 size and DC resistance at 20 °C",
    "alternateName": "AWG and kcmil to mm²: sizes and resistance",
    "description": "Conversion table for the 20 conductor sizes used in North American wiring, 18 AWG to 500 kcmil: diameter (in, mm), area in circular mils and mm², the next standard IEC 60228 metric size up, and the DC resistance at 20 °C of a solid copper and aluminium conductor of that area (Ω/km and Ω/1000 ft). Every value is computed from the ASTM B258 AWG definition and standard resistivities (copper 0.017241, aluminium 1350 0.028264 Ω·mm²/m); the rounded circular-mil values printed in US code tables are included for comparison. The table behind the AWG to mm² converter on zhukovskyi.space and the Electrician Calc app.",
    "url": "https://zhukovskyi.space/calculators/electrical/awg-to-mm2.html",
    "version": "1.0.0",
    "datePublished": "2026-11-25",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "AWG",
        "American Wire Gauge",
        "mm2",
        "kcmil",
        "circular mils",
        "wire size",
        "IEC 60228",
        "conductor resistance",
        "electrical",
        "unit conversion"
    ],
    "citation": "Zhukovskyi, A. (2026). AWG and kcmil wire sizes in mm², circular mils, diameter, nearest IEC 60228 size and DC resistance at 20 °C (Version 1.0.0) [Data set]. Dre Dev. https://doi.org/10.5281/zenodo.24545621",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "size",
            "description": "Size as written in the trade: 12 AWG, 1/0 AWG, 250 kcmil."
        },
        {
            "@type": "PropertyValue",
            "name": "awg",
            "description": "AWG number (1/0 to 4/0 as written); empty for kcmil sizes."
        },
        {
            "@type": "PropertyValue",
            "name": "kcmil",
            "description": "Thousand circular mils; empty for AWG sizes.",
            "unitText": "kcmil"
        },
        {
            "@type": "PropertyValue",
            "name": "diameter_in",
            "description": "Diameter of a solid round conductor of this area.",
            "unitText": "in"
        },
        {
            "@type": "PropertyValue",
            "name": "diameter_mm",
            "description": "diameter_in × 25.4.",
            "unitText": "mm"
        },
        {
            "@type": "PropertyValue",
            "name": "area_cmil",
            "description": "Area from the ASTM B258 formula (AWG) or the size itself (kcmil).",
            "unitText": "circular mil"
        },
        {
            "@type": "PropertyValue",
            "name": "area_cmil_printed",
            "description": "The rounded value printed in US code tables and used by the calculators.",
            "unitText": "circular mil"
        },
        {
            "@type": "PropertyValue",
            "name": "area_mm2",
            "description": "area_cmil × 0.000506707479.",
            "unitText": "mm²"
        },
        {
            "@type": "PropertyValue",
            "name": "next_iec_60228_mm2",
            "description": "Smallest IEC 60228 standard size at least as large as area_mm2. Not an ampacity equivalent.",
            "unitText": "mm²"
        },
        {
            "@type": "PropertyValue",
            "name": "r20_cu_ohm_per_km",
            "description": "DC resistance at 20 °C, solid annealed copper (0.017241 Ω·mm²/m).",
            "unitText": "Ω/km"
        },
        {
            "@type": "PropertyValue",
            "name": "r20_al_ohm_per_km",
            "description": "DC resistance at 20 °C, aluminium 1350 (0.028264 Ω·mm²/m).",
            "unitText": "Ω/km"
        },
        {
            "@type": "PropertyValue",
            "name": "r20_cu_ohm_per_kft",
            "description": "Copper, per 1000 ft.",
            "unitText": "Ω/1000 ft"
        },
        {
            "@type": "PropertyValue",
            "name": "r20_al_ohm_per_kft",
            "description": "Aluminium, per 1000 ft.",
            "unitText": "Ω/1000 ft"
        }
    ],
    "distribution": [
        {
            "@type": "DataDownload",
            "encodingFormat": "text/csv",
            "contentUrl": "https://zenodo.org/records/24545621/files/awg-to-mm2.csv?download=1"
        },
        {
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": "https://zenodo.org/records/24545621/files/awg-to-mm2.json?download=1"
        }
    ],
    "sameAs": [
        "https://doi.org/10.5281/zenodo.24545621"
    ],
    "identifier": [
        "https://doi.org/10.5281/zenodo.24545621",
        "doi:10.5281/zenodo.24545621"
    ]
}

# open-data/shift-rota-patterns (built 2026-11-26), without distribution and sameAs: with_doi() adds them.
SHIFT_PATTERNS_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/shifts/#dataset",
    "name": "Shift rota patterns written out day by day: 4 on 4 off, 2-2-3 Pitman, DuPont, Continental and others, with average hours per week and days off per year",
    "alternateName": "Shift rota patterns: hours and days off",
    "description": "Thirteen common shift rotas, each written out day by day as a string of letters (D day, N night, E early, L late, X 8-hour night, T 10-hour day, W 9 to 5, F 24-hour, O off), with the cycle as runs, the cycle length, shifts and days off per cycle, the shift length, hours per cycle, the average hours per week (hours per cycle ÷ cycle days × 7), the average days off per year (days off per cycle ÷ cycle days × 365.25), the longest run of shifts and the longest break. It covers the six patterns of the free shift calendars on zhukovskyi.space (4 on 4 off, 2-2-3 Pitman, DuPont, 3 on 3 off, 4 on 3 off, Continental) and the eleven presets of the ShiftWise shift calendar app (with its default shift times); where a pattern is in both, the two sequences are checked to be the same. Every number is computed from the cycle; scheduled hours only, without unpaid breaks, leave or overtime.",
    "url": "https://zhukovskyi.space/calculators/shifts/",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "shift work",
        "shift pattern",
        "rota",
        "roster",
        "4 on 4 off",
        "2-2-3",
        "Pitman",
        "DuPont",
        "Continental",
        "12-hour shifts",
        "working time"
    ],
    "citation": "Zhukovskyi, A. (2026). Shift rota patterns written out day by day: 4 on 4 off, 2-2-3 Pitman, DuPont, Continental and others, with average hours per week and days off per year (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/shifts/",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "pattern",
            "description": "Short key, the same as in the ShiftWise app and the site's code."
        },
        {
            "@type": "PropertyValue",
            "name": "name",
            "description": "Name of the pattern."
        },
        {
            "@type": "PropertyValue",
            "name": "cycle",
            "description": "One letter per day of the cycle: D day, N night (12 h), E early, L late, X night (8 h), T 10-hour day, W 9 to 5, F 24-hour, O off."
        },
        {
            "@type": "PropertyValue",
            "name": "cycle_runs",
            "description": "The cycle as runs of the same letter, for example D×4 O×4."
        },
        {
            "@type": "PropertyValue",
            "name": "cycle_days",
            "description": "Length of the cycle.",
            "unitText": "days"
        },
        {
            "@type": "PropertyValue",
            "name": "shifts_per_cycle",
            "description": "Working days in one cycle.",
            "unitText": "shifts"
        },
        {
            "@type": "PropertyValue",
            "name": "days_off_per_cycle",
            "description": "Days off in one cycle.",
            "unitText": "days"
        },
        {
            "@type": "PropertyValue",
            "name": "shift_types",
            "description": "The letters used, with shift length and, for ShiftWise presets, the app's default start and end times."
        },
        {
            "@type": "PropertyValue",
            "name": "shift_hours",
            "description": "Scheduled length of each shift (every shift of a pattern has the same length).",
            "unitText": "h"
        },
        {
            "@type": "PropertyValue",
            "name": "hours_per_cycle",
            "description": "shifts_per_cycle × shift_hours.",
            "unitText": "h"
        },
        {
            "@type": "PropertyValue",
            "name": "avg_hours_per_week",
            "description": "hours_per_cycle ÷ cycle_days × 7.",
            "unitText": "h/week"
        },
        {
            "@type": "PropertyValue",
            "name": "days_off_per_year",
            "description": "days_off_per_cycle ÷ cycle_days × 365.25.",
            "unitText": "days/year"
        },
        {
            "@type": "PropertyValue",
            "name": "longest_run_of_shifts",
            "description": "Most shifts in a row, counting across the end of the cycle into the next.",
            "unitText": "shifts"
        },
        {
            "@type": "PropertyValue",
            "name": "longest_break_days",
            "description": "Most days off in a row, counting across the end of the cycle.",
            "unitText": "days"
        },
        {
            "@type": "PropertyValue",
            "name": "in_shiftwise_app",
            "description": "yes if the pattern is a preset in the ShiftWise app."
        },
        {
            "@type": "PropertyValue",
            "name": "site_page",
            "description": "The pattern's calendar page on zhukovskyi.space; empty if there is none."
        },
        {
            "@type": "PropertyValue",
            "name": "sequence_source",
            "description": "Where the day-by-day sequence was read (URLs), or the ShiftWise preset."
        }
    ],
    "isBasedOn": [
        "https://en.wikipedia.org/wiki/Shift_plan",
        "https://soon.works/shift-patterns/pitman",
        "https://soon.works/shift-patterns/continental",
        "https://soon.works/shift-patterns",
        "https://www.rosterelf.com/uk/guides/shift-patterns"
    ]
}

# open-data/public-holidays-rest-rules (built 2026-11-26), the same way.
HOLIDAYS_REST_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/shifts/public-holidays-and-rest.html#dataset",
    "name": "Minimum daily rest between shifts by country, with the statute, and public holidays of the UK, Ireland, Germany, Spain, France, Italy, the Netherlands, Poland, Brazil, Mexico, the United States and Ukraine",
    "alternateName": "Rest between shifts and public holidays",
    "description": "Two tables for shift workers and rota software. The main table has one row per country or UK region (England and Wales, Scotland, Northern Ireland, Ireland, Germany, Spain, France, Italy, the Netherlands, Poland, Brazil, Mexico, the United States, Ukraine): the minimum daily rest between working days as the national law states it (11 hours in the UK, Ireland, the EU countries listed and Brazil, 12 in Spain, twice the previous shift in Ukraine, no general rule in Mexico or US federal law), the statute and article with a link to the official text read on 26 November 2026, where the public holidays come from, and the 2027 holiday list. The second table (public-holidays.csv) lists every public holiday with its date, weekday and name: UK bank holidays 2019–2028 from gov.uk (Open Government Licence v3.0, one-off holidays and substitute days included), and the national holidays of the other countries for 2026–2028, computed from their statutory rules and checked against the dates the ShiftWise shift calendar app uses. Regional and local holidays are not included.",
    "url": "https://zhukovskyi.space/calculators/shifts/public-holidays-and-rest.html",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "public holidays",
        "bank holidays",
        "daily rest",
        "rest between shifts",
        "working time",
        "Working Time Directive",
        "11 hours rest",
        "shift work",
        "labour law",
        "holiday calendar"
    ],
    "citation": "Zhukovskyi, A. (2026). Minimum daily rest between shifts by country, with the statute, and public holidays of the UK, Ireland, Germany, Spain, France, Italy, the Netherlands, Poland, Brazil, Mexico, the United States and Ukraine (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/shifts/public-holidays-and-rest.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "region",
            "description": "Key: england-and-wales, scotland, northern-ireland, or the country (ireland, germany …)."
        },
        {
            "@type": "PropertyValue",
            "name": "country_code",
            "description": "ISO 3166-1 alpha-2 code."
        },
        {
            "@type": "PropertyValue",
            "name": "region_name",
            "description": "Name of the country or UK region."
        },
        {
            "@type": "PropertyValue",
            "name": "min_daily_rest_hours",
            "description": "Minimum consecutive rest between working days for adult workers; empty where the law sets no fixed number of hours.",
            "unitText": "h"
        },
        {
            "@type": "PropertyValue",
            "name": "rest_rule",
            "description": "The rule in plain English, with the built-in exceptions."
        },
        {
            "@type": "PropertyValue",
            "name": "rest_law",
            "description": "Statute and article."
        },
        {
            "@type": "PropertyValue",
            "name": "rest_law_url",
            "description": "Official text read on 26 November 2026."
        },
        {
            "@type": "PropertyValue",
            "name": "holidays_scope",
            "description": "Which holidays are listed and their legal basis."
        },
        {
            "@type": "PropertyValue",
            "name": "holidays_source_url",
            "description": "Official source of the holiday rules; empty for Germany (the 16 state laws)."
        },
        {
            "@type": "PropertyValue",
            "name": "holiday_years",
            "description": "Years in public-holidays.csv for this region."
        },
        {
            "@type": "PropertyValue",
            "name": "holidays_in_2027",
            "description": "Number of public holidays in 2027.",
            "unitText": "days"
        },
        {
            "@type": "PropertyValue",
            "name": "holidays_2027",
            "description": "The 2027 holidays: date and name, separated by semicolons."
        }
    ],
    "isBasedOn": [
        "https://www.gov.uk/bank-holidays.json",
        "https://www.legislation.gov.uk/uksi/1998/1833/regulation/10",
        "https://www.legislation.gov.uk/nisr/2016/49/regulation/12",
        "https://revisedacts.lawreform.ie/eli/1997/act/20/section/11/revised/en/html",
        "https://www.gesetze-im-internet.de/arbzg/__5.html",
        "https://www.boe.es/buscar/act.php?id=BOE-A-2015-11430",
        "https://code.travail.gouv.fr/code-du-travail/l3131-1",
        "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2003-04-08;66~art7",
        "https://wetten.overheid.nl/jci1.3:c:BWBR0007671&hoofdstuk=5&paragraaf=5.2&artikel=5:3",
        "https://api.sejm.gov.pl/eli/acts/DU/2026/1245/text.pdf",
        "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
        "https://www.diputados.gob.mx/LeyesBiblio/pdf/LFT.pdf",
        "https://www.dol.gov/agencies/whd/overtime",
        "https://zakon.rada.gov.ua/laws/show/322-08",
        "https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/"
    ]
}



def dataset_ld(ds, ld):
    """A Dataset as its page shows it: the DOI and the Zenodo downloads are added once DOI[ds] is filled in."""
    out = dict(ld, **doi_props(ds))
    if DOI[ds]:
        record = DOI[ds].rsplit(".", 1)[1]
        out["distribution"] = [{"@type": "DataDownload", "encodingFormat": kind,
                                "contentUrl": f"https://zenodo.org/records/{record}/files/{ds}.{ext}?download=1"}
                               for ext, kind in (("csv", "text/csv"), ("json", "application/json"))]
    return out


# Copied from experimental/open-data (schema-org-dataset.jsonld, built by its build.py) without the mirror and
# download fields, which point nowhere until the Zenodo record exists; dataset_ld() adds them from DOI.
ROOF_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/roofing/roof-pitch-multiplier-chart.html#dataset",
    "name": "Roof pitch multipliers 1/12 to 24/12: angle, grade, slope (rafter) factor and hip/valley factor",
    "alternateName": "Roof pitch multipliers: 1/12 to 24/12",
    "description": "Reference table for the 24 whole-inch roof pitches from 1/12 to 24/12 (rise in inches per 12 in of run): the roof angle in degrees, the grade in percent, the slope factor (common rafter length and sloped roof area per unit of horizontal run, √(144 + rise²) ÷ 12), the hip and valley factor (hip or valley length per unit of common run when both planes share the pitch, √(288 + rise²) ÷ 12), and the same two values as inches of rafter per foot of run, as printed on a framing square. Every value is computed from right-triangle geometry, so anyone can reproduce it. The table behind the roof pitch multiplier chart on zhukovskyi.space and the RoofCalc app.",
    "url": "https://zhukovskyi.space/calculators/roofing/roof-pitch-multiplier-chart.html",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "roof pitch",
        "roof slope",
        "pitch multiplier",
        "slope factor",
        "rafter length",
        "hip and valley factor",
        "roofing",
        "roof area",
        "framing square",
        "construction"
    ],
    "citation": "Zhukovskyi, A. (2026). Roof pitch multipliers 1/12 to 24/12: angle, grade, slope (rafter) factor and hip/valley factor (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/roofing/roof-pitch-multiplier-chart.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "pitch",
            "description": "Pitch as written in the trade: rise per 12 in of run, for example 6/12."
        },
        {
            "@type": "PropertyValue",
            "name": "rise_in",
            "description": "Rise in inches per 12 in of horizontal run.",
            "unitText": "in"
        },
        {
            "@type": "PropertyValue",
            "name": "run_in",
            "description": "Run, always 12 in.",
            "unitText": "in"
        },
        {
            "@type": "PropertyValue",
            "name": "angle_deg",
            "description": "Roof angle from horizontal: atan(rise ÷ 12), 4 decimals.",
            "unitText": "°"
        },
        {
            "@type": "PropertyValue",
            "name": "grade_pct",
            "description": "Rise ÷ run × 100, 2 decimals.",
            "unitText": "%"
        },
        {
            "@type": "PropertyValue",
            "name": "slope_factor",
            "description": "√(144 + rise²) ÷ 12: sloped length (common rafter, roof area) per unit of horizontal run, 5 decimals."
        },
        {
            "@type": "PropertyValue",
            "name": "hip_valley_factor",
            "description": "√(288 + rise²) ÷ 12: hip or valley length per unit of common run, both planes at this pitch, 5 decimals."
        },
        {
            "@type": "PropertyValue",
            "name": "common_rafter_in_per_ft_run",
            "description": "√(144 + rise²): inches of common rafter per foot of run (slope_factor × 12).",
            "unitText": "in/ft"
        },
        {
            "@type": "PropertyValue",
            "name": "hip_rafter_in_per_ft_run",
            "description": "√(288 + rise²): inches of hip or valley rafter per foot of common run (hip_valley_factor × 12).",
            "unitText": "in/ft"
        }
    ]
}

REBAR_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/concrete/rebar-size-chart.html#dataset",
    "name": "Reinforcing bar sizes of the US (#3–#18), Europe (Ø6–Ø40) and Canada (10M–55M): nominal diameter, area and mass computed at 7,850 kg/m³",
    "alternateName": "Rebar sizes: US, EU and Canada (area, mass)",
    "description": "One row for each of 30 reinforcing bar sizes: US inch-pound bars #3 to #18 (ASTM A615/A615M), European bars Ø6 to Ø40 mm (EN 10080 preferred series) and Canadian metric bars 10M to 55M (CSA G30.18). Each row has the nominal diameter in mm and inches, and the cross-sectional area (mm², in²) and mass (kg/m, lb/ft) computed by the author from that diameter: area = π/4 × d², mass = area × 7,850 kg/m³. Only the nominal diameters come from the standards, as printed in free public tables (Caltrans Bridge Design Details 13.1, Hong Kong CS2:2012, RSIC Manual of Standard Practice); the nominal areas and masses printed in the standards are rounded and can differ from these by up to 0.6 % (Canadian 15M: 1.570 kg/m printed, 1.578 computed from 16.0 mm). The table behind the rebar size chart on zhukovskyi.space and the rebar tools of the SlabCalc app.",
    "url": "https://zhukovskyi.space/calculators/concrete/rebar-size-chart.html",
    "version": "1.0.0",
    "datePublished": "2026-11-26",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "isAccessibleForFree": True,
    "inLanguage": "en",
    "creator": {
        "@type": "Person",
        "@id": "https://zhukovskyi.space/#person",
        "name": "Andrii Zhukovskyi",
        "url": "https://zhukovskyi.space/"
    },
    "publisher": {
        "@id": "https://zhukovskyi.space/#dredev"
    },
    "keywords": [
        "rebar",
        "reinforcing bar",
        "rebar sizes",
        "rebar weight",
        "ASTM A615",
        "EN 10080",
        "CSA G30.18",
        "concrete",
        "construction",
        "unit conversion"
    ],
    "citation": "Zhukovskyi, A. (2026). Reinforcing bar sizes of the US (#3–#18), Europe (Ø6–Ø40) and Canada (10M–55M): nominal diameter, area and mass computed at 7,850 kg/m³ (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/concrete/rebar-size-chart.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "system",
            "description": "US (inch-pound bar numbers), EU (European metric) or CA (Canadian metric)."
        },
        {
            "@type": "PropertyValue",
            "name": "designation",
            "description": "Bar size as written: #4, Ø12, 15M."
        },
        {
            "@type": "PropertyValue",
            "name": "standard",
            "description": "Standard that defines the size: ASTM A615/A615M, EN 10080 or CSA G30.18."
        },
        {
            "@type": "PropertyValue",
            "name": "nominal_diameter_mm",
            "description": "Nominal diameter (US bars: the inch value × 25.4).",
            "unitText": "mm"
        },
        {
            "@type": "PropertyValue",
            "name": "nominal_diameter_in",
            "description": "Nominal diameter in inches, 4 decimals.",
            "unitText": "in"
        },
        {
            "@type": "PropertyValue",
            "name": "area_mm2",
            "description": "π/4 × d², computed, 2 decimals.",
            "unitText": "mm²"
        },
        {
            "@type": "PropertyValue",
            "name": "area_in2",
            "description": "area_mm2 ÷ 645.16, 4 decimals.",
            "unitText": "in²"
        },
        {
            "@type": "PropertyValue",
            "name": "mass_kg_per_m",
            "description": "area × 7,850 kg/m³, computed, 4 decimals.",
            "unitText": "kg/m"
        },
        {
            "@type": "PropertyValue",
            "name": "weight_lb_per_ft",
            "description": "mass_kg_per_m × 0.3048 ÷ 0.45359237, 4 decimals.",
            "unitText": "lb/ft"
        },
        {
            "@type": "PropertyValue",
            "name": "diameter_checked_in",
            "description": "Key of the free published table the nominal diameter was checked in (URLs in the JSON and README); empty for Ø14 and Ø28."
        }
    ],
    "isBasedOn": [
        "https://dot.ca.gov/-/media/dot-media/programs/engineering/documents/bridgedesigndetails/chapter-12/202509bdd131reinforcement-a11y.pdf",
        "https://www.cedd.gov.hk/filemanager/eng/content_77/cs2_2012.pdf",
        "https://rebar.org/"
    ]
}
