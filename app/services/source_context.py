SOURCES: dict[str, str] = {
    "parabens": "NIH, EWG - linked to endocrine disruption",
    "paraben": "NIH, EWG - linked to endocrine disruption",
    "methylparaben": "NIH, EWG - linked to endocrine disruption",
    "propylparaben": "NIH, EWG - linked to endocrine disruption",
    "bpa": "FDA, WHO - hormone mimicry in plastics",
    "bisphenol a": "FDA, WHO - hormone mimicry in plastics",
    "phthalates": "NIH - reproductive health concerns",
    "phthalate": "NIH - reproductive health concerns",
    "fragrance": "EWG - undisclosed chemical mixtures, potential irritant",
    "synthetic fragrance": "EWG - undisclosed chemical mixtures, potential irritant",
    "parfum": "EWG - undisclosed chemical mixtures, potential irritant",
    "triclosan": "FDA - antimicrobial resistance, thyroid disruption",
    "sulfates": "EWG - skin and eye irritant, strips natural oils",
    "sls": "EWG - skin and eye irritant, strips natural oils",
    "sles": "EWG - skin and eye irritant, strips natural oils",
    "sodium lauryl sulfate": "EWG - skin and eye irritant, strips natural oils",
    "sodium laureth sulfate": "EWG - skin and eye irritant, strips natural oils",
    "formaldehyde": "NIH, IARC - classified as carcinogen",
    "oxybenzone": "EWG - potential endocrine disruptor, coral reef damage",
    "dea": "EWG - linked to organ toxicity",
    "diethanolamine": "EWG - linked to organ toxicity",
}


def build_source_context(flagged_ingredients: list) -> str:
    lines = []
    seen = set()

    for ingredient in flagged_ingredients:
        # Handle both flat strings and structured dicts
        if isinstance(ingredient, dict):
            name = ingredient.get("name", "")
        else:
            name = str(ingredient)

        key = name.lower().strip()
        if key in SOURCES and key not in seen:
            lines.append(f"{name} - {SOURCES[key]}")
            seen.add(key)

    return "\n".join(lines)
