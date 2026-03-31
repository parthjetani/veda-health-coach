from app.services.source_context import build_source_context, SOURCES


class TestBuildSourceContext:
    def test_known_ingredients(self):
        result = build_source_context(["Parabens", "BPA"])
        assert "NIH" in result
        assert "FDA" in result
        assert "Parabens" in result
        assert "BPA" in result

    def test_unknown_ingredient(self):
        result = build_source_context(["XylitolMagic3000"])
        assert result == ""

    def test_mixed_known_unknown(self):
        result = build_source_context(["Fragrance", "UnknownChemical"])
        assert "EWG" in result
        assert "UnknownChemical" not in result

    def test_empty_list(self):
        result = build_source_context([])
        assert result == ""

    def test_case_insensitive(self):
        result = build_source_context(["PARABENS", "bpa"])
        assert "NIH" in result
        assert "FDA" in result

    def test_no_duplicates(self):
        result = build_source_context(["Parabens", "parabens", "PARABENS"])
        lines = result.strip().split("\n")
        assert len(lines) == 1

    def test_all_known_sources_covered(self):
        assert "parabens" in SOURCES
        assert "bpa" in SOURCES
        assert "phthalates" in SOURCES
        assert "fragrance" in SOURCES
        assert "triclosan" in SOURCES
        assert "sulfates" in SOURCES
