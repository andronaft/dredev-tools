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
    "vpd-table": "10.5281/zenodo.24547085",
    "brix-plato-specific-gravity": "10.5281/zenodo.24547087",
}


def doi_props(ds):
    """identifier + sameAs for a Dataset whose copy on Zenodo has this DOI."""
    doi = DOI.get(ds, "")
    if not doi:  # not published on Zenodo yet
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


# Datasets from experimental/open-data that are not on Zenodo yet (vpd-table, brix-plato-specific-gravity). Copied
# from their schema-org-dataset.jsonld without the download links, which only exist once there is a DOI.

def with_doi(ld, ds, files):
    """The Dataset block, plus identifier, sameAs and Zenodo downloads once DOI[ds] is filled in."""
    out = dict(ld)
    props = doi_props(ds)
    if props:
        record = DOI[ds].rsplit(".", 1)[1]
        out.update(props)
        out["distribution"] = [{"@type": "DataDownload", "encodingFormat": "text/csv" if f.endswith(".csv") else "application/json",
                                "contentUrl": f"https://zenodo.org/records/{record}/files/{f}?download=1"} for f in files]
    return out


VPD_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/hydroponics/vpd-chart.html#dataset",
    "name": "Vapour pressure deficit (VPD) table by air temperature and relative humidity, with leaf VPD and dew point, from FAO-56 Eq. 11",
    "alternateName": "VPD table: 15–35 °C × 30–90 % RH (FAO-56)",
    "description": "Vapour pressure deficit for every whole degree from 15 to 35 °C and every 5 % relative humidity from 30 to 90 % (273 rows): saturation vapour pressure e°(T) from FAO Irrigation and Drainage Paper 56, Eq. 11 (Allen et al., 1998), the actual vapour pressure, the air VPD (leaf at air temperature), the leaf VPD for a leaf 2 °C cooler than the air (the default of the GrowLab app), and the dew point. Every value is computed; the formula reproduces all 21 e° values FAO prints in Annex 2, Table 2.3 for 15–35 °C to the third decimal. The table behind the VPD chart on zhukovskyi.space and the GrowLab hydroponics app. No target bands are included: crop VPD targets are guidance, not data.",
    "url": "https://zhukovskyi.space/calculators/hydroponics/vpd-chart.html",
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
        "vapour pressure deficit",
        "VPD",
        "VPD chart",
        "relative humidity",
        "saturation vapour pressure",
        "FAO-56",
        "dew point",
        "leaf temperature",
        "greenhouse",
        "hydroponics"
    ],
    "citation": "Zhukovskyi, A. (2026). Vapour pressure deficit (VPD) table by air temperature and relative humidity, with leaf VPD and dew point, from FAO-56 Eq. 11 (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/hydroponics/vpd-chart.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "air_temp_c",
            "description": "Air temperature, 15 to 35 in steps of 1.",
            "unitText": "°C"
        },
        {
            "@type": "PropertyValue",
            "name": "rh_pct",
            "description": "Relative humidity of the air, 30 to 90 in steps of 5.",
            "unitText": "%"
        },
        {
            "@type": "PropertyValue",
            "name": "es_air_kpa",
            "description": "Saturation vapour pressure at the air temperature, FAO-56 Eq. 11: 0.6108 × exp(17.27 T / (T + 237.3)).",
            "unitText": "kPa"
        },
        {
            "@type": "PropertyValue",
            "name": "ea_kpa",
            "description": "Actual vapour pressure of the air: es_air_kpa × rh_pct / 100.",
            "unitText": "kPa"
        },
        {
            "@type": "PropertyValue",
            "name": "vpd_air_kpa",
            "description": "Air VPD (leaf at air temperature): es_air_kpa − ea_kpa.",
            "unitText": "kPa"
        },
        {
            "@type": "PropertyValue",
            "name": "leaf_temp_c",
            "description": "Leaf temperature used for the leaf VPD: air temperature − 2 °C (GrowLab's default offset).",
            "unitText": "°C"
        },
        {
            "@type": "PropertyValue",
            "name": "es_leaf_kpa",
            "description": "Saturation vapour pressure at the leaf temperature (Eq. 11).",
            "unitText": "kPa"
        },
        {
            "@type": "PropertyValue",
            "name": "vpd_leaf_kpa",
            "description": "Leaf VPD: es_leaf_kpa − ea_kpa. Negative where the leaf is at or below the dew point (condensation).",
            "unitText": "kPa"
        },
        {
            "@type": "PropertyValue",
            "name": "dew_point_c",
            "description": "Dew point: Eq. 11 solved for the temperature at which e° = ea_kpa.",
            "unitText": "°C"
        }
    ],
    "isBasedOn": [
        "https://www.fao.org/4/x0490e/x0490e07.htm",
        "https://www.fao.org/4/x0490e/x0490e0j.htm"
    ]
}


BRIX_LD = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    "@id": "https://zhukovskyi.space/calculators/brewing/brix-plato-sg-chart.html#dataset",
    "name": "Degrees Brix and Plato to specific gravity, gravity points and potential alcohol, 0 to 40 degrees in steps of 0.5",
    "alternateName": "Brix / Plato to specific gravity, 0–40 °",
    "description": "Conversion table from degrees Brix or Plato (sugar % by weight) to specific gravity for 0 to 40 degrees in steps of 0.5 (81 rows), with gravity points, the ASBC polynomial back to degrees, and the potential alcohol by volume if the wort or must ferments to 1.000 by the standard homebrew formula (OG − FG) × 131.25 and by Michael Hall's formula (Zymurgy, 1995). Degrees to SG uses the equation Brewer's Friend publishes as the Lyons equation; Brix and Plato are treated as one scale, as homebrew tools do. Every value is computed; the SG matches the US National Bureau of Standards sucrose table (Circular C457, apparent SG 20/20 °C) to five decimals up to 10 °Bx and within 0.0003 up to 40 °Bx. The table behind the Brix, Plato and SG chart on zhukovskyi.space and the Ferment app.",
    "url": "https://zhukovskyi.space/calculators/brewing/brix-plato-sg-chart.html",
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
        "Brix",
        "Plato",
        "specific gravity",
        "Brix to SG",
        "Plato to SG",
        "hydrometer",
        "homebrewing",
        "mead",
        "cider",
        "potential alcohol"
    ],
    "citation": "Zhukovskyi, A. (2026). Degrees Brix and Plato to specific gravity, gravity points and potential alcohol, 0 to 40 degrees in steps of 0.5 (Version 1.0.0) [Data set]. Dre Dev. https://zhukovskyi.space/calculators/brewing/brix-plato-sg-chart.html",
    "variableMeasured": [
        {
            "@type": "PropertyValue",
            "name": "degrees",
            "description": "Degrees Brix or Plato (sugar % by weight), 0 to 40 in steps of 0.5.",
            "unitText": "°Bx / °P"
        },
        {
            "@type": "PropertyValue",
            "name": "sg",
            "description": "Specific gravity: 1 + degrees / (258.6 − (degrees / 258.2 × 227.1)), the Lyons equation as published by Brewer's Friend.",
            "unitText": "SG"
        },
        {
            "@type": "PropertyValue",
            "name": "gravity_points",
            "description": "(sg − 1) × 1000: 1.050 is 50 points.",
            "unitText": "points"
        },
        {
            "@type": "PropertyValue",
            "name": "degrees_back_asbc",
            "description": "The ASBC polynomial applied to sg: −616.868 + 1111.14 SG − 630.272 SG² + 135.997 SG³. Shows how far the two published formulas disagree.",
            "unitText": "°P"
        },
        {
            "@type": "PropertyValue",
            "name": "potential_abv_pct",
            "description": "Alcohol if it ferments to 1.000: (sg − 1.000) × 131.25.",
            "unitText": "% ABV"
        },
        {
            "@type": "PropertyValue",
            "name": "potential_abv_hall_pct",
            "description": "The same by Michael Hall's formula: 76.08 (OG − FG) / (1.775 − OG) × FG / 0.794, FG = 1.000.",
            "unitText": "% ABV"
        }
    ],
    "isBasedOn": [
        "https://www.brewersfriend.com/brix-converter/",
        "https://www.brewersfriend.com/plato-to-sg-conversion-chart/",
        "https://www.brewersfriend.com/2011/06/16/alcohol-by-volume-calculator-updated/",
        "https://nvlpubs.nist.gov/nistpubs/Legacy/circ/nbscircular457.pdf"
    ]
}
