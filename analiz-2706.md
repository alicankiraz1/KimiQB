# KimiQB 27 Haziran Parite Analizi

## Kapsam

- Kaynak: yan checkout `CodexQB`
- Hedef: bu checkout `KimiQB`
- KimiQB dalı: `codex/kimiqb-021-gate-integrity-port`
- KimiQB HEAD: `1caf3c3 Port KimiQB session apply integrity`
- CodexQB HEAD: `8cd4b78 Update README release validation notes`

Bu analiz CodexQB'nin güncel Goal/Apply bütünlük davranışını KimiQB'deki Kimi Code şekliyle karşılaştırır. CodexQB kaynak klasörü salt okunur kabul edildi; uygulama hedefi KimiQB repo kökü ve managed Kimi Code kopyasıdır.

## Sonuç

Kritik runtime/validator parite açığı bulunmadı. KimiQB'de CodexQB'nin son Goal/Apply güvenlik davranışlarının Kimi uyarlamaları mevcut: `session_policy_digest`, `apply_policy_digest`, strict validator checkpoint'leri, selected READY queue snapshot kapsamı, Git-aware workspace inventory, `Review-Package.patch` hash kontrolü, planned validation evidence hash zorunluluğu ve `state: proposed` ile sözleşmeye bağlı yeni dosya kabulü.

Eksikler daha çok release kanıtı, fixture kapsamı ve public dokümantasyon netliği tarafında.

## Parite Matrisi

| Alan | CodexQB kanıtı | KimiQB durumu | Aksiyon |
| --- | --- | --- | --- |
| Public manifest | Codex plugin metadata ve Codex skill invocation | `kimi.plugin.json`, `/skill:kimiqb`, `version: 0.3.0` | Taşınmış |
| Planner validator | strict Step 2/3/4, Ledger, ontology, comprehension kontrolleri | `skills/kimiqb/scripts/validate_planner_docs.py` aynı sınıf kontrolleri Kimi pathleriyle çalıştırıyor | Taşınmış |
| Session/Goal compiler | Codex `goal_run.py` policy envelope ve strict checkpoints | Kimi `session_run.py` içinde `session_policy_digest`, strict checkpoints, selected subplan scope | Taşınmış |
| Apply controller | `apply_policy_digest`, workspace baseline, patch/evidence hash doğrulaması | Kimi `apply_run.py` aynı semantiği `kimi_session_serial` ve `.kimiqb` altında uyguluyor | Taşınmış |
| Codex-only yüzeyler | Codex plugin manifesti, Codex agent config'i, Codex skill invocation, Codex runtime wording | Kimi tarafında public yüzey Kimi Code dilinde tutulmuş | Taşınmamalı |
| Fixture corpus | Codex fixture seti 20 senaryo | Kimi fixture corpus 7 planner/comprehension senaryosu; session/apply davranışı ayrı smoke/unit testlerle kapsanıyor | Genişletilebilir |
| Release evidence docs | Codex `docs/FEEDBACK-CLOSURE-AUDIT.md`, release audit ve live subagent evidence tutuyor | Kimi'de eşdeğer public release audit dosyası yok | Public release gate istenirse eklenmeli |
| README public netliği | Codex README 0.3.0 digest, source binding ve release validation ayrıntılarını anlatıyor | Kimi README 0.3.0'u anlatıyor ama digest/patch/evidence-hash detayları daha görünür olmalı | Güncellendi |

## KimiQB'ye Taşınmaması Gerekenler

- Codex plugin manifesti ve Codex marketplace metadata.
- Codex agent config dosyaları.
- Codex skill invocation adı.
- Codex runtime ve Codex subagent wording'i.
- Codex'e özel `.codexqb` runtime pathleri.

KimiQB tarafında bunların karşılığı `kimi.plugin.json`, `/skill:kimiqb`, `${KIMI_SKILL_DIR}`, Kimi Code session wording'i, `.kimiqb` runtime pathleri ve managed copy parity akışıdır.

## Önerilen Sonraki Dilim

1. Kimi fixture corpus'u CodexQB'nin 20 senaryolu setine yaklaştır: apply/no-action/resume/security/stale snapshot/export senaryolarını Kimi adlarıyla ekle.
2. Public release kanıtı isteniyorsa Kimi uyarlamalı `docs/FEEDBACK-CLOSURE-AUDIT.md` ve `docs/release-audits/0.3.0-feedback-closure.md` ekle.
3. Bu audit dosyaları eklenirse `scripts/validate.sh` ve `tests/test_skill_content.py` içinde release-audit varlığı zorunlu hale getir.
4. Managed copy sync sonrası repo-managed SHA/parite kontrolünü release notuna kaydet.

## Doğrulama Komutları

Bu port için önerilen yerel doğrulama sırası:

```bash
python3 evals/run_fixture_corpus_checks.py
python3 evals/run_apply_behavior_smoke.py
python3 evals/run_downstream_session_apply_dry_run.py
python3 evals/run_session_apply_metric_checks.py
python3 -m unittest discover -s tests -v
make check
git diff --check
make export-sanitized
```

Sanitized paket ayrıca git metadata olmadan açılıp şu komutla kontrol edilmeli:

```bash
KIMIQB_VALIDATE_SKIP_UNITTESTS=1 make check
```

Kimi Code tarafına uygulama için managed copy sync sonrası `/plugins reload` veya `/new` gerekir.
