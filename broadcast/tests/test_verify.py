from templates import build_templates
from verify import verify_line

SQUAD = [
    "Robert Hampstead",
    "Andrew Hornsey",
    "David Rochdale",
    "James Dickenson",
    "Robert Oxford",
]
BUNDLE = {
    "clocks": ["87:05"],
    "scores": ["5-1"],
    "names": ["Robert Hampstead", "Arsesnail", "Mancheater City"],
    "numbers": ["87:05", "5", "1", "0.43"],
}


def test_verifier_rejects_the_bad_lines():
    good = "87:05. Robert Hampstead scores. Arsesnail 5–1 Mancheater City."
    assert verify_line(good, BUNDLE, SQUAD) == []
    assert any("score" in error for error in verify_line("87:05. Arsesnail 9–0 Mancheater City.", BUNDLE, SQUAD))
    assert any("clock" in error for error in verify_line("88:05. Robert Hampstead scores.", BUNDLE, SQUAD))
    assert any("name" in error for error in verify_line("87:05. Robert Oxford scores. Arsesnail 5–1 Mancheater City.", BUNDLE, SQUAD))
    assert any("real club" in error for error in verify_line("87:05. Arsenal score.", BUNDLE, SQUAD))
    assert any("prediction" in error for error in verify_line("Arsesnail will win.", BUNDLE, SQUAD))


def test_every_template_line_passes_on_the_way_in():
    built = build_templates(SQUAD)
    assert [moment["id"] for moment in built["moments"]] == [
        "open",
        "hampstead",
        "push",
        "rochdale",
        "dickenson",
        "recap",
    ]
    assert built["moments"][1]["t"] == 5
    assert "Hornsey" not in built["moments"][2]["lines"]["classic"]["en"]["neutral"]["call"]
