from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "skills/kimiqb/scripts/validate_planner_docs.py"

STEP1_HEADINGS = [
    "# Main Planing",
    "## 1. Yönetici Özeti",
    "## 2. Proje Vizyonu",
    "## 3. Mevcut Durum Analizi",
    "## 4. Hedef Son Durum",
    "## 5. Mimari Yön ve Ana Kararlar",
    "## 6. Fazlara Bölünmüş Ana Yol Haritası",
    "## 7. Kritik Riskler ve Açıklar",
    "## 8. Önceliklendirilmiş Sonraki Adımlar",
    "## 9. Step 2 İçin Hazırlık Notları",
    "## 10. Repo İnceleme Notları",
]

AUTOPSY_HEADINGS = [
    "# Project Autopsy",
    "## 1. Yönetici Özeti",
    "## 2. İncelenen Kaynaklar",
    "## 3. Proje Bölümleri ve Sorumluluk Alanları",
    "## 4. Feature Envanteri",
    "## 5. Placeholder, Stub ve Skeleton Analizi",
    "## 6. Teknik Borç ve Bakım Riskleri",
    "## 7. Hatalı veya Eksik Entegrasyonlar",
    "## 8. Test, CI ve Doğrulama Açıkları",
    "## 9. Güvenlik, Secret ve Governance Bulguları",
    "## 10. Operasyonel Readiness ve Gözlemlenebilirlik",
    "## 11. Ana Planla Uyumluluk Analizi",
    "## 12. Step 2 İçin Autopsy Feedbackleri",
    "## 13. Öncelikli Düzeltme ve Planlama Sinyalleri",
]

INDEX_HEADINGS = [
    "# Sub-Planing Index",
    "## 1. Amaç",
    "## 2. Kaynak Ana Plan",
    "## 3. Faz ve Alt Plan Haritası",
    "## 4. Öncelikli Detaylandırma Sırası",
    "## 5. Kapsam Dışı Bırakılan veya Ertelenen Konular",
    "## 6. Coverage Kontrolü",
    "## 7. Repo İnceleme Notları",
]

SUBPLAN_HEADINGS = [
    "## 1. Bağlam",
    "## 2. Hedef",
    "## 3. Açıklama",
    "## 4. Kapsam",
    "## 5. Kapsam Dışı",
    "## 6. Mevcut Repo Kanıtı",
    "## 7. Planlanan İş Kırılımı",
    "## 8. Kabul Kriterleri",
    "## 9. Doğrulama ve Test Yaklaşımı",
    "## 10. Bağımlılıklar ve Sıralama",
    "## 11. Riskler ve Önlemler",
    "## 12. Varmak İstenen Nokta",
    "## 13. Sonraki Alt Faza Geçiş Kriteri",
]

AUDIT_HEADINGS = [
    "# Sub-Planing Audit",
    "## 1. Denetim Özeti",
    "## 2. İncelenen Kaynaklar",
    "## 3. Ana Faz Kapsama Analizi",
    "## 4. Alt Plan Dosya Envanteri",
    "## 5. Naming ve Sıralama Kontrolü",
    "## 6. Index Tutarlılık Kontrolü",
    "## 7. Zorunlu Bölüm Yapısı Kontrolü",
    "## 8. İçerik Kalitesi ve Uygulanabilirlik Analizi",
    "## 9. Scope Drift ve Mimari Tutarlılık Analizi",
    "## 10. Readiness Gerçekçiliği",
    "## 11. Güvenlik ve Governance Bulguları",
    "## 12. Step 4 Hazırlık Değerlendirmesi",
    "## 13. Öncelikli Düzeltme Listesi",
    "## 14. Önerilen Sonraki Komut / Prompt",
    "## 15. Denetim Sonucu",
]


def body(label: str) -> str:
    clean_label = label.lstrip("# ").replace("|", " ").strip()
    return f"{clean_label} bölümü için yeterli uzunlukta, doğrulanabilir ve Türkçe fixture açıklaması."


def run_validator(root: Path, mode: str, strict: bool = False) -> subprocess.CompletedProcess[str]:
    command = ["python3", str(VALIDATOR), "--root", str(root), "--mode", mode]
    if strict:
        command.append("--strict")
    return subprocess.run(command, text=True, capture_output=True, check=False)


def write_main_plan(docs: Path) -> None:
    lines: list[str] = []
    for heading in STEP1_HEADINGS:
        lines += [heading, "", body(heading), ""]
        if heading == "## 6. Fazlara Bölünmüş Ana Yol Haritası":
            lines += [
                "Mevcut repo Faz 0B-10 tarihsel planlarını ve Phase 11 güvenlik notlarını içerir.",
                "",
                "| Faz | Faz adı | Hedef | Yaklaşık olgunluk | Ana kabul sinyalleri |",
                "|---|---|---|---|---|",
                "| 1 | Local Contract Stabilizasyonu | Baseline netleştirme | M3 | make check |",
                "| 2 | Live Gateway Aktivasyonu | ready_live kanıtı | M4 | make smoke |",
                "",
            ]
    (docs / "Main-Planing.md").write_text("\n".join(lines), encoding="utf-8")


def write_autopsy(docs: Path, headings: list[str] | None = None) -> None:
    lines: list[str] = []
    for heading in headings or AUTOPSY_HEADINGS:
        lines += [heading, "", body(heading), ""]
    (docs / "Autopsy.md").write_text("\n".join(lines), encoding="utf-8")


def write_subplan(path: Path, phase: int, subphase: int) -> None:
    lines = [f"# Faz {phase}.{subphase} — Test Alt Plan", ""]
    for heading in SUBPLAN_HEADINGS:
        text = body(heading)
        if heading == "## 6. Mevcut Repo Kanıtı":
            text += " `configs/example.placeholder` normal bir örnek dosya adıdır."
        if heading == "## 11. Riskler ve Önlemler":
            text += " placeholder-safe komut anlatımı gerçek placeholder değildir."
        lines += [heading, "", text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_index(docs: Path, relative_refs: bool = False) -> None:
    refs = [
        "Faz-1-Plans/Faz1.1-local-contract.md",
        "./Planner-docs/Faz-2-Plans/Faz2.1-live-gateway.md",
    ] if relative_refs else [
        "Planner-docs/Faz-1-Plans/Faz1.1-local-contract.md",
        "Planner-docs/Faz-2-Plans/Faz2.1-live-gateway.md",
    ]

    lines: list[str] = []
    for heading in INDEX_HEADINGS:
        lines += [heading, "", body(heading), ""]
        if heading == "## 3. Faz ve Alt Plan Haritası":
            lines += [f"- {ref}" for ref in refs] + [""]
    (docs / "Sub-Planing-Index.md").write_text("\n".join(lines), encoding="utf-8")


def write_audit(docs: Path, status: str, fixes: list[str] | None = None) -> None:
    lines: list[str] = []
    for heading in AUDIT_HEADINGS:
        lines += [heading, "", body(heading), ""]
        if heading == "## 1. Denetim Özeti":
            lines += [f"Denetim durumu: {status}", ""]
        if heading == "## 13. Öncelikli Düzeltme Listesi":
            for fix in fixes or []:
                lines += [fix, ""]
        if heading == "## 15. Denetim Sonucu":
            lines += [f"Nihai durum: {status}", ""]
    (docs / "Sub-Planing-Audit.md").write_text("\n".join(lines), encoding="utf-8")


def write_valid_step2_fixture(root: Path, relative_refs: bool = False) -> Path:
    docs = root / "Planner-docs"
    (docs / "Faz-1-Plans").mkdir(parents=True)
    (docs / "Faz-2-Plans").mkdir(parents=True)
    write_main_plan(docs)
    write_index(docs, relative_refs=relative_refs)
    write_subplan(docs / "Faz-1-Plans/Faz1.1-local-contract.md", 1, 1)
    write_subplan(docs / "Faz-2-Plans/Faz2.1-live-gateway.md", 2, 1)
    return docs


class ValidatePlannerDocsTests(unittest.TestCase):
    def test_step2_passes_when_autopsy_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_valid_step2_fixture(Path(temp_dir))
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("autopsy_exists=false", result.stdout)

    def test_step2_validates_optional_autopsy_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_autopsy(docs)
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("autopsy_exists=true", result.stdout)

    def test_step2_rejects_autopsy_heading_order_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            bad_headings = AUTOPSY_HEADINGS.copy()
            bad_headings[3], bad_headings[4] = bad_headings[4], bad_headings[3]
            write_autopsy(docs, headings=bad_headings)
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("heading_out_of_order=Planner-docs/Autopsy.md", result.stdout)

    def test_roadmap_table_ignores_historical_phase_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_valid_step2_fixture(Path(temp_dir))
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("main_phase_count=2", result.stdout)
            self.assertNotIn("Faz-10-Plans", result.stdout)
            self.assertNotIn("Faz-11-Plans", result.stdout)

    def test_placeholder_safe_and_example_placeholder_are_not_false_positive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_valid_step2_fixture(Path(temp_dir))
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("placeholder_text=", result.stdout)

    def test_relative_index_refs_are_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_valid_step2_fixture(Path(temp_dir), relative_refs=True)
            result = run_validator(Path(temp_dir), "step2", strict=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("index_reference_count=2", result.stdout)

    def test_long_secret_is_detected_but_short_task_spec_like_text_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            (docs / "task-spec.yaml").write_text("name: task-spec.yaml\nexample: sk-short\n", encoding="utf-8")
            short_result = run_validator(Path(temp_dir), "step2")
            self.assertEqual(short_result.returncode, 0, short_result.stdout + short_result.stderr)
            self.assertIn("secret_findings=0", short_result.stdout)

            (docs / "leak.md").write_text("fake test token: sk-" + "A" * 24 + "\n", encoding="utf-8")
            long_result = run_validator(Path(temp_dir), "step2")
            self.assertNotEqual(long_result.returncode, 0, long_result.stdout + long_result.stderr)
            self.assertIn("secret_pattern=openai_api_key", long_result.stdout)

    def test_step4_missing_audit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            write_valid_step2_fixture(Path(temp_dir))
            result = run_validator(Path(temp_dir), "step4")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("missing_file=Planner-docs/Sub-Planing-Audit.md", result.stdout)

    def test_step4_blocked_audit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_audit(docs, "BLOCKED")
            result = run_validator(Path(temp_dir), "step4")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("step4_blocked_by_audit_status=BLOCKED", result.stdout)

    def test_step4_pass_audit_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_audit(docs, "PASS")
            result = run_validator(Path(temp_dir), "step4")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("audit_status=PASS", result.stdout)

    def test_step4_pass_with_warnings_blocks_on_p0_or_p1(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_audit(docs, "PASS_WITH_WARNINGS", ["- AUDIT-FIX-01 | P1 | repair before implementation"])
            result = run_validator(Path(temp_dir), "step4")
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("step4_blocked_by_high_severity_findings=P0:0,P1:1", result.stdout)

    def test_step4_pass_with_only_p2_or_p3_warns_but_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_audit(docs, "PASS_WITH_WARNINGS", ["- AUDIT-FIX-02 | P2 | nonblocking wording repair"])
            result = run_validator(Path(temp_dir), "step4")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("warning=step4_has_nonblocking_warnings=P2:1,P3:0", result.stdout)

    def test_step4_pass_with_warnings_no_findings_text_does_not_count_as_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            docs = write_valid_step2_fixture(Path(temp_dir))
            write_audit(docs, "PASS_WITH_WARNINGS", ["P0/P1 bulgusu yok. P2/P3 bulgusu yok."])
            result = run_validator(Path(temp_dir), "step4")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("p0_findings=0", result.stdout)
            self.assertIn("p1_findings=0", result.stdout)
            self.assertIn("p2_findings=0", result.stdout)
            self.assertIn("p3_findings=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
