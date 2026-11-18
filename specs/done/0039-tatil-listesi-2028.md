# Spec 0039 — tatil-listesi-2028 (mini)

- Status: Shipped
- Mode: lite
- Plan: `specs/plans/0039-plan.md`
- Source: `docs/domain.md` OD-10 (istek: İbrahim Gürhan, 2026-11-18)
- Design: — (ekran düzeni değişmez; yalnız 2028 tarihli taleplerin gün sayısı. Açılış verisinde
  2028 tarihli talep yok, ekran görüntüsünde fark olmaz; kanıt testlerdir)
- Supersedes: 0014/K-4'ün 2028 kısmı ("2028 ve sonrası: yalnız hafta sonu düşülür" → 2029 ve
  sonrası); 0014'ün listeyi K-2'ye birebir eşitleyen kanıtı (liste artık K-2 + 2028)

## Intent
İzin günü iş günüdür (BR-3) ve resmî tatiller kodda sabit bir listededir; liste bugün yalnız
2026–2027'yi kapsıyor. 2028'e uzanan bir talepte (ör. 1–5 Mayıs 2028) hafta içine denk gelen
tatiller de bakiyeden düşülüyor. 2028 resmî tatilleri listeye eklenir; listenin bakımı (2029 ve
sonrası) açık karar olarak kalır.

## Kararlar (clarify)
- **K-1 2028 resmî tatilleri (2429 sayılı Kanun; dini bayramlar Diyanet takvimi):** 1 Ocak,
  23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, 29 Ekim; Ramazan Bayramı 26–28 Şubat 2028;
  Kurban Bayramı 5–8 Mayıs 2028. Toplam 14 tarih; hafta içine denk gelenler 6: 28 Şubat (Pzt),
  1 Mayıs (Pzt), 5 Mayıs (Cum), 8 Mayıs (Pzt), 19 Mayıs (Cum), 30 Ağustos (Çar).
- **K-2 Teyit:** dini bayram tarihleri Hicri takvime bağlı; IK, PLAN öncesi Diyanet'in 2028 dini
  günler takvimi ya da Resmî Gazete'den teyit eder. Bir tarih değişirse spec değişikliğidir (R-08).
- **K-3 Arife yarım günleri 2028** (25 Şubat Cuma, 4 Mayıs Perşembe, 28 Ekim Cumartesi): 0014/K-3
  gibi **tam iş günü** sayılır (OD-9 değişmez).
- **K-4 Liste dışı yıllar:** 2026 öncesi ve 2029 ve sonrası; yalnız hafta sonu düşülür, uyarı ya
  da red yok (0014/K-4 kuralı, sınır bir yıl ileri).
- **K-5 Tek hesap:** bakiye, Kullanılan, Bekleyen, onay ve Talepler ekranının "Gun" sütunu aynı
  hesabı kullanır (0014/K-1; değişmez).

## Changed behavior
- [x] CB-1 — **2028 tatilleri sayılmaz:** K-1'deki 14 tarihin her biri tek başına 0 gün;
  1–5 Mayıs 2028 → 3 (bugün 5); 28 Şubat–3 Mart 2028 → 4 (bugün 5); 28 Ağustos–1 Eylül 2028 → 4
  (bugün 5); 8 Mayıs 2028 → 0.
- [x] CB-2 — **2028 arifeleri tam gün:** 25 Şubat 2028 → 1; 4 Mayıs 2028 → 1; 28 Ekim 2028
  (Cumartesi) → 0.
- [x] CB-3 — **Liste dışı sınırı 2029:** 1 Ocak 2029 (Pzt) → 1 gün (liste dışı yıl, yalnız hafta
  sonu düşülür).
- [x] CB-4 — **Ekran ve bakiye aynı sayıyı kullanır:** 1–5 Mayıs 2028 için yeni talep kaydedilir
  ve Talepler ekranında "Gun" 3 görünür. Bakiye kontrolü de 3 günle yapılır: kullanılabilir
  bakiyesi (Kalan − Bekleyen) tam 3 gün olan personelin bu talebi kaydedilir (bugün 5 gün
  sayıldığı için "yetersiz bakiye" ile reddediliyor), 2 gün olanınki reddedilir.
- [x] CB-5 — **Alan dokümanı:** `docs/domain.md` BR-3'te liste 2026–2028; OD-10 güncellenir
  (liste 2028 sonuna kadar; 2029 için 2028 sonundan önce bakım, karar spec 0039).

## Preserved behavior
- [x] PB-1 — **2026–2027 listesi aynen:** 0014'ün 27 tarihi listede, her biri 0 gün; 2026–2027
  arifeleri tam gün (0014 testleri değişmeden yeşil).
- [x] PB-2 — **Liste öncesi yıllar:** 1 Ocak 2025 (Çar) → 1 gün; 2028'in tatil içermeyen
  haftası 3–7 Ocak 2028 → 5.
- [x] PB-3 — **Açılış verisi ve ekranlar aynı:** Talepler ekranındaki gün sayıları ve ana sayfa
  bakiyeleri değişmez (açılış talepleri 2026'da).
- [x] PB-4 — **Geri kalan her şey aynı:** iş günü yok kuralı ve mesajı, ters tarih, bakiye
  mesajları, uzun aralığın hızlı sayımı (0014 S-1), yetki ve ekran düzeni değişmez;
  `./scripts/check` yeşil.

## Out of scope
- 2029 ve sonrası tatiller; IK'nın tatil girdiği ekran (OD-8 sonrası, OD-10'da kalır).
- Arife yarım günlerinin yarım sayılması (OD-9).
- Hafta tatilinin değişmesi, köprü günleri / idari izinler (genelgeyle verilen ek tatiller kanunla
  resmî tatil değildir).

## Verification (VERIFY, 2026-11-18, HEAD `d460114`)
CB-1…CB-5 ve PB-1…PB-4 Pass (bağımsız QA alt ajanı); full `CHECK GREEN (full, 3 steps, 58 s)`
(827 passed, 5 skipped, `ac99435`; sonrası yalnız spec/plan). Repo dışı kopyada (`git archive`)
`domain/workdays.py`'ye 9 mutant: Ramazan 2028 yok 3, Kurban 2028 yok 6, yıllıklar 2028'siz 6,
liste 2029'a uzar 2, 25 Şubat arifesi tatil 2, 28 Şubat yok 3, 8 Mayıs yok 3, fazladan 9 Mayıs 1
test kırmızı; `main` kodu HEAD testleriyle 8 kırmızı. Üretim diff'i yalnız `domain/workdays.py`;
`tests/`'te silinen satırlar yalnız supersede edilen liste testi ve bir yorum. Review round 1
temiz: F-1 (Low, plan haritasında PB-2 test adı) real — kanıt tablosunda doğru adla kapatıldı;
F-2 (Info, 107 karakterlik yorum) noise. UI düzeni değişmedi; 1–5 Mayıs 2028 talebinin Talepler
ekranında "Gun 3" görüntüsü PR'da (plan Risk 3). Ayrıntı: `specs/plans/0039-plan.md` "Triage" ve
"Verify".

## Definition of Done
- [x] `scripts/check` green
- [x] Independent review done; real findings fixed, noise rejected with written rationale
- [x] Criterion ↔ evidence table complete for CB-* **and** PB-* (UI: before/after screenshots)
- [x] Spec moved to `specs/done/` (immutable there)
