"""Reference facts shown on the HVAC and electrical pages, each with the page it was read on.

Rule: a number is only here if it was read on the source page on the date in CHECKED. A fact with no reliable
source has no entry, and the pages then leave the field out. Pressures are not here: they come from the PT tables
that build.py loads from hvac-charge-app.
"""

CHECKED = "12 November 2026"
CHECKED_ISO = "2026-11-12"

# key -> (title shown on the page, URL)
SOURCES = {
    "epa_tt": ("US EPA, Technology Transitions GWP Reference Table (page updated 2 April 2026)",
               "https://www.epa.gov/climate-hfcs-reduction/technology-transitions-gwp-reference-table"),
    "epa_ods": ("US EPA, Ozone-Depleting Substances (page updated 9 April 2026)",
                "https://www.epa.gov/ozone-layer-protection/ozone-depleting-substances"),
    "snap_ac": ("US EPA SNAP, Substitutes in Residential and Light Commercial Air Conditioning and Heat Pumps (page updated 19 March 2026)",
                "https://www.epa.gov/snap/substitutes-residential-and-light-commercial-air-conditioning-and-heat-pumps"),
    "snap_food": ("US EPA SNAP, Substitutes in Refrigerated Food Processing and Dispensing Equipment (page updated 20 March 2026)",
                  "https://www.epa.gov/snap/substitutes-refrigerated-food-processing-and-dispensing-equipment"),
    "snap_transport": ("US EPA SNAP, Substitutes in Refrigerated Transport (page updated 20 March 2026)",
                       "https://www.epa.gov/snap/substitutes-refrigerated-transport"),
    "snap_household": ("US EPA SNAP, Substitutes in Household Refrigerators and Freezers (page updated 16 March 2026)",
                       "https://www.epa.gov/snap/substitutes-household-refrigerators-and-freezers"),
    "snap_industrial": ("US EPA SNAP, Substitutes in Industrial Process Refrigeration (page updated 19 March 2026)",
                        "https://www.epa.gov/snap/substitutes-industrial-process-refrigeration"),
    "arkema_digest": ("Arkema, 2025 Forane® Technical Digest",
                      "https://forane.arkema.com/files/live/sites/shared_arkema/files/Fluorochemicals/2025%20Forane%20Technical%20Digest-FINAL-LR.pdf"),
    "arkema_407a": ("Arkema, Forane® 407A data sheet",
                    "https://www.arkema.com/files/live/sites/shared_arkema/files/downloads/products/fluorochemicals/Forane-407A.pdf"),
    "nri_r408a": ("National Refrigerants, R-408A Product Data Summary (2020)",
                  "https://refrigerants.com/wp-content/uploads/2020/03/R408A_RefGuid.pdf"),
    "nri_r409a": ("National Refrigerants, R-409A Product Data Summary (2020)",
                  "https://refrigerants.com/wp-content/uploads/2020/03/R409A_RefGuid.pdf"),
    "nri_r12": ("National Refrigerants, R-12 Product Data Summary (2020)",
                "https://refrigerants.com/wp-content/uploads/2020/03/R12_RefGuid.pdf"),
    "nri_r1234yf": ("National Refrigerants, R-1234yf Product Data Summary (2020)",
                    "https://refrigerants.com/wp-content/uploads/2020/03/R1234yf_RefGuid.pdf"),
    "carrier_ph5": ("Carrier PH5SAN5 single-stage heat pump with R-454B, Installation Instructions",
                    "https://www.shareddocs.com/hvac/docs/1009/Public/0A/PH5SAN5-01SI.pdf"),
    "carrier_llg": ("Carrier, Residential Piping and Long Line Guideline for AC and heat pumps using R-454B",
                    "https://www.shareddocs.com/hvac/docs/1009/Public/03/LLG-R454B-01.pdf"),
    "lennox_ml13": ("Lennox ML13KC1 Installation Instructions 508732-02 (03/2026)",
                    "https://www.lennox.com/dA/60bad3149d/508732-02.pdf"),
    "york_yh9": ("York YH9/XH9 R-454B heat pump Installation Manual 6515371-UIM-B-0526",
                 "https://doral.yorknow.com/pub/media/documentation/yh9_installguide.pdf"),
    "chemours_pt": ("Chemours, Opteon™ XL41 (R-454B) Pressure-Temperature Guide for A/C",
                    "https://www.opteon.com/en/-/media/files/opteon/a2l/optxlptac-0522-printable.pdf?rev=745c0b46b0524377a315c8a9c606d238&sc_lang=en"),
    "chemours_xl41": ("Chemours, Opteon™ XL41 (R-454B) product information (C-11001, 7/24)",
                      "https://www.opteon.com/en/-/media/files/opteon/opteon-xl41-product-information.pdf?la=en"),
    "arkema_pt_2019": ("Arkema, Forane® Pressure-Temperature Chart, wall chart for the Americas (2019)",
                       "https://forane.arkema.com/files/live/sites/fluorogases_forane_arkema/files/downloads/literature/general-forane-literature/forane-wall-chart-americas.pdf"),
    "arkema_pt_2025": ("Arkema, Forane® Refrigerants Pressure Temperature Chart (PPC/SDC 05-2025)",
                       "https://forane.arkema.com/files/live/sites/shared_arkema/files/downloads/fluorochemicals/Forane%20Ref%20PT%20Regular%20Chart%20EN"),
    "bryant_tsh": ("Bryant 563C/563G split-system air conditioners, wiring diagram 324476-101 Rev. B (2-04), "
                   "Table I: Superheat Charging Table",
                   "https://inspectapedia.com/aircond/Bryant-split-system-ac-wiring.pdf"),
}

# 100-year GWP exactly as printed: refrigerant -> (value, source key, basis the page states).
# One publisher for every page: US EPA. Its Technology Transitions table where the refrigerant is listed, otherwise
# EPA's ozone-depleting substances list (R-22, R-12) or its SNAP list. Makers' literature differs by a unit or two
# (Arkema's digest prints 466 for R-454B, 2,138 for R-427A, 1,397 for R-449A, 631 for R-513A): not mixed in.
GWP = {
    "R-410A": ("2,088", "epa_tt", "AR4, calculated for the blend"),
    "R-454B": ("465", "epa_tt", "AR4, calculated for the blend"),
    "R-32": ("675", "epa_tt", "IPCC 2007 (AR4)"),
    "R-22": ("1,810", "epa_ods", "AR4"),
    "R-134a": ("1,430", "epa_tt", "IPCC 2007 (AR4)"),
    "R-404A": ("3,922", "epa_tt", "AR4, calculated for the blend"),
    "R-407C": ("1,774", "epa_tt", "AR4, calculated for the blend"),
    "R-407A": ("2,110", "snap_food", "SNAP list"),
    "R-448A": ("1,386", "epa_tt", "AR4, calculated for the blend"),
    "R-449A": ("1,396", "epa_tt", "AR4, calculated for the blend"),
    "R-452A": ("2,140", "epa_tt", "AR4, calculated for the blend"),
    "R-513A": ("630", "epa_tt", "AR4, calculated for the blend"),
    "R-1234yf": ("1", "epa_tt", "WMO 2022"),
    "R-507A": ("3,985", "epa_tt", "AR4, calculated for the blend"),
    "R-427A": ("2,140", "snap_food", "SNAP list"),
    "R-408A": ("3,152", "snap_food", "SNAP list"),
    "R-409A": ("1,558", "snap_food", "SNAP list"),
    "R-290": ("3.3", "epa_tt", "IPCC 2007 (AR4)"),
    "R-600a": ("1", "epa_tt", "WMO 2022"),
    "R-744": ("1", "epa_tt", "IPCC 2007 (AR4)"),
    "R-717": ("1", "epa_tt", "WMO 2022"),
    "R-12": ("10,900", "epa_ods", "AR4"),
}

# Ozone depletion potential, only for the refrigerants that have one: refrigerant -> (value, source key).
ODP = {
    "R-22": ("0.055", "epa_ods"),
    "R-12": ("1", "epa_ods"),
    "R-408A": ("0.026", "snap_food"),
    "R-409A": ("0.047", "snap_food"),
}

# EPA page whose "ASHRAE Designation (Safety Classification)" column prints the same class as the app's data.
# R-717: the app uses B2L, EPA's SNAP pages print B2; R-12 is not on the SNAP pages read. Both stay without a link.
SAFETY_SOURCE = {
    "R-410A": "snap_ac", "R-454B": "snap_ac", "R-32": "snap_ac", "R-22": "snap_food", "R-134a": "snap_ac",
    "R-404A": "snap_ac", "R-407C": "snap_ac", "R-407A": "snap_ac", "R-448A": "snap_food", "R-449A": "snap_food",
    "R-452A": "snap_transport", "R-513A": "snap_ac", "R-1234yf": "snap_food", "R-507A": "snap_ac",
    "R-427A": "snap_ac", "R-408A": "snap_food", "R-409A": "snap_food", "R-290": "snap_ac",
    "R-600a": "snap_household", "R-744": "snap_food",
}
SAFETY_WORDS = {
    "A1": "lower toxicity, no flame propagation",
    "A2L": "lower toxicity, lower flammability",
    "A3": "lower toxicity, higher flammability",
    "B2L": "higher toxicity, lower flammability",
}

# Compressor lubricant as the refrigerant maker states it: refrigerant -> (text, source key).
# Not listed (no maker statement read): R-507A, R-290, R-600a, R-744, R-717.
OIL = {
    "R-410A": ("POE (polyolester)", "arkema_digest"),
    "R-454B": ("POE (polyolester)", "arkema_digest"),
    "R-32": ("POE (polyolester)", "arkema_digest"),
    "R-22": ("Mineral oil, alkylbenzene or POE", "arkema_digest"),
    "R-134a": ("POE; PAG in automotive AC only", "arkema_digest"),
    "R-404A": ("POE (polyolester)", "arkema_digest"),
    "R-407C": ("POE (polyolester)", "arkema_digest"),
    "R-407A": ("POE (polyolester)", "arkema_407a"),
    "R-448A": ("POE (polyolester)", "arkema_digest"),
    "R-449A": ("POE (polyolester)", "arkema_digest"),
    "R-452A": ("POE (polyolester)", "arkema_digest"),
    "R-513A": ("POE (polyolester)", "arkema_digest"),
    "R-1234yf": ("PAG in automotive systems; POE can be used in refrigeration", "nri_r1234yf"),
    "R-427A": ("Mineral oil, alkylbenzene or POE; the maker recommends POE", "arkema_digest"),
    "R-408A": ("Mineral oil, alkylbenzene or POE", "nri_r408a"),
    "R-409A": ("Mineral oil, alkylbenzene or POE", "nri_r409a"),
    "R-12": ("Mineral oil", "nri_r12"),
}

# What the maker says the refrigerant replaces: refrigerant -> (text, source key).
REPLACES = {
    "R-454B": ("R-410A, in new equipment only", "arkema_digest"),
    "R-32": ("R-410A, in new equipment", "arkema_digest"),
    "R-134a": ("R-12", "arkema_digest"),
    "R-404A": ("R-502", "arkema_digest"),
    "R-407C": ("R-22", "arkema_digest"),
    "R-407A": ("R-404A and R-507A", "arkema_407a"),
    "R-448A": ("R-404A, R-507A, R-22 and the R-407 series", "arkema_digest"),
    "R-449A": ("R-404A, R-507A, R-22 and the R-407 series", "arkema_digest"),
    "R-452A": ("R-404A and R-507A", "arkema_digest"),
    "R-513A": ("R-134a, except in automotive AC", "arkema_digest"),
    "R-427A": ("R-22, as a retrofit", "arkema_digest"),
    "R-408A": ("R-502", "nri_r408a"),
    "R-409A": ("R-12 and R-500", "nri_r409a"),
}

# Blend composition as the maker prints it: refrigerant -> (text, source key). Only where a maker document was read.
COMPOSITION = {
    "R-454B": ("R-32 / R-1234yf, 68.9 / 31.1 % by weight", "chemours_xl41"),
}

# A page note where the table on the site knowingly differs from a printed chart: refrigerant -> (text, source keys).
PT_NOTES = {
    "R-427A": ("At 150 °F the 2025 edition of Arkema's chart prints 456.8 and 467.4 psig for R-427A. Those are the R-404A and "
               "R-507A cells of the same row, and a vapor pressure above the liquid pressure cannot be right. This page uses the "
               "2019 edition, which prints 418.9 and 388.8 psig; every other R-427A row is the same in both editions.",
               ("arkema_pt_2019", "arkema_pt_2025")),
}
