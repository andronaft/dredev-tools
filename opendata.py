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
    "pool-chlorine-dose": "10.5281/zenodo.24547075",
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

# Copied from experimental/open-data/pool-chlorine-dose/schema-org-dataset.jsonld (built 26 November 2026), without
# sameAs and distribution: the dataset is not on Zenodo yet. Fill DOI["pool-chlorine-dose"] once it is.
POOL_CHLORINE_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/pool/how-much-chlorine-to-add.html#dataset",
    "name": "Pool chlorine dose to raise free chlorine by 1 ppm, with the stabilizer (CYA) and calcium each product adds: liquid chlorine, bleach, cal-hypo, dichlor and trichlor",
    "alternateName": "Pool chlorine dose per 1 ppm, 8 products",
    "description": "How much of each common pool chlorine product raises free chlorine by 1 ppm (1 mg/L as Cl2): liquid chlorine 10 % and 12.5 % (trade percent), household bleach 6 % and 8.25 % (weight % NaOCl), calcium hypochlorite 65 % and 73 %, dichlor 56 % and trichlor 90 % (weight % available chlorine). For each product: grams of available chlorine per litre (liquids), the dose per 10,000 US gallons (US fl oz or oz), per m³ and per 10 m³ (mL or g), the available chlorine of the pure compound, and how much stabilizer (cyanuric acid) or calcium hardness (as CaCO3) each 1 ppm of chlorine leaves in the water. Computed by stoichiometry from the CIAAW 2024 standard atomic weights and the available-chlorine definitions; the density of bleach is interpolated in the OxyChem Sodium Hypochlorite Handbook (Table 2). The table behind the pool chlorine calculator on zhukovskyi.space and the PoolPro app.",
    "url": "https://zhukovskyi.space/calculators/pool/how-much-chlorine-to-add.html",
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
        "pool chlorine",
        "free chlorine",
        "ppm",
        "sodium hypochlorite",
        "bleach",
        "calcium hypochlorite",
        "trichlor",
        "dichlor",
        "cyanuric acid",
        "pool chemistry"
    ],
    "citation": "Zhukovskyi, A. (2026). Pool chlorine dose to raise free chlorine by 1 ppm, with the stabilizer (CYA) and calcium each product adds: liquid chlorine, bleach, cal-hypo, dichlor and trichlor (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/pool/how-much-chlorine-to-add.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "product_id",
            "description": "Short id, the same as the calculator uses (liquid10, bleach6, calhypo65 …)."
        },
        {
            "@type": "PropertyValue",
            "name": "product",
            "description": "Product as sold, with its common label strength."
        },
        {
            "@type": "PropertyValue",
            "name": "form",
            "description": "liquid or solid."
        },
        {
            "@type": "PropertyValue",
            "name": "active_compound",
            "description": "The chlorine compound: NaOCl, Ca(OCl)2, sodium dichloroisocyanurate dihydrate, trichloroisocyanuric acid."
        },
        {
            "@type": "PropertyValue",
            "name": "label_strength_pct",
            "description": "The strength printed on the label, on the basis in strength_basis.",
            "unitText": "%"
        },
        {
            "@type": "PropertyValue",
            "name": "strength_basis",
            "description": "What the label percent means: trade % (g available chlorine per 100 mL), weight % NaOCl, or weight % available chlorine."
        },
        {
            "@type": "PropertyValue",
            "name": "specific_gravity",
            "description": "Bleach only: specific gravity at 60 °F interpolated in OxyChem Table 2. Empty where not needed."
        },
        {
            "@type": "PropertyValue",
            "name": "available_chlorine_g_per_l",
            "description": "Liquids: grams of available chlorine (as Cl2) per litre.",
            "unitText": "g/L"
        },
        {
            "@type": "PropertyValue",
            "name": "available_chlorine_wt_pct",
            "description": "Weight % available chlorine: the label value for solids, g/L ÷ (10 × SG) for bleach; empty for trade-percent liquids (density not given).",
            "unitText": "%"
        },
        {
            "@type": "PropertyValue",
            "name": "pure_compound_available_chlorine_pct",
            "description": "Available chlorine of the pure active compound, from molar masses (upper bound for the label).",
            "unitText": "%"
        },
        {
            "@type": "PropertyValue",
            "name": "dose_per_10000_usgal",
            "description": "Amount that raises free chlorine by 1 ppm in 10,000 US gallons: US fl oz for liquids, avoirdupois oz for solids.",
            "unitText": "US fl oz or oz"
        },
        {
            "@type": "PropertyValue",
            "name": "dose_unit_us",
            "description": "US fl oz or oz (weight)."
        },
        {
            "@type": "PropertyValue",
            "name": "dose_per_m3",
            "description": "Amount that raises 1 m³ (1,000 L) by 1 ppm: mL for liquids, g for solids.",
            "unitText": "mL or g"
        },
        {
            "@type": "PropertyValue",
            "name": "dose_per_10_m3",
            "description": "The same for 10 m³.",
            "unitText": "mL or g"
        },
        {
            "@type": "PropertyValue",
            "name": "dose_unit_metric",
            "description": "mL or g."
        },
        {
            "@type": "PropertyValue",
            "name": "cya_ppm_per_ppm_fc",
            "description": "Cyanuric acid (stabilizer) added with each 1 ppm of free chlorine; 0 for unstabilized products.",
            "unitText": "ppm per ppm"
        },
        {
            "@type": "PropertyValue",
            "name": "calcium_hardness_ppm_per_ppm_fc",
            "description": "Calcium hardness (as CaCO3) added with each 1 ppm of free chlorine; 0 except cal-hypo.",
            "unitText": "ppm CaCO3 per ppm"
        }
    ],
    "isBasedOn": [
        "https://www.ciaaw.org/abridged-atomic-weights.htm",
        "https://www.forceflowscales.com/downloads/chemical-safety/hypochlorite/Hypo_Handbook_Oxy_Chem.pdf"
    ]
}
POOL_CHLORINE_LD.update(doi_props("pool-chlorine-dose"))
