"""The open datasets published on Zenodo (26 November 2026) and their schema.org markup.

The DOIs tie the site's Dataset markup to the Zenodo records, so Google Dataset Search treats them as one dataset.
GWP_LD and AWG_LD are copied from experimental/open-data (schema-org-dataset.jsonld, built by its build.py); the
refrigerant-pt and NEC pages build their own Dataset and only add the DOI here.
"""

DOI = {
    "refrigerant-pt": "10.5281/zenodo.24545607",
    "nec-edition-by-state": "10.5281/zenodo.24545613",
    "refrigerant-gwp-safety": "10.5281/zenodo.24545617",
    "awg-to-mm2": "10.5281/zenodo.24545621",
    "aquarium-ammonia-fraction": "10.5281/zenodo.24547079",
    "seawater-salinity-specific-gravity": "10.5281/zenodo.24547081",
}


def doi_props(ds):
    """identifier + sameAs for a Dataset whose copy on Zenodo has this DOI; nothing while the DOI is still empty."""
    doi = DOI[ds]
    if not doi:
        return {}
    return {"identifier": [f"https://doi.org/{doi}", f"doi:{doi}"], "sameAs": [f"https://doi.org/{doi}"]}


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
