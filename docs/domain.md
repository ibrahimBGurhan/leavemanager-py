# Domain

> Bootstrap'te (2026-10-23) dolduruldu. Kuralların referans kaynağı **4857 sayılı İş Kanunu
> md. 53 ve 56** ile güncel IK yönetmeliğidir. Kanundan türetilen ama henüz IK tarafından
> onaylanmamış kurallar **[IK onayı bekliyor]** ile işaretlidir. **Mevcut kod** satırları bugünkü
> davranışı anlatır; karakterizasyon testleri bunu sabitler, değişiklik `/change` ile yapılır.

## Ubiquitous language

| Term | Meaning | Notes / not to be confused with |
|---|---|---|
| Personel (`Employee`) | İzin hakkı olan çalışan: ad, birim, işe giriş tarihi | Kullanıcı hesabı değildir (auth henüz yok) |
| Birim (`department`) | Personelin bağlı olduğu departman (IT, Muhasebe, IK, Satis…) | |
| İzin Talebi (`LeaveRequest`) | Bir personelin başlangıç–bitiş tarihli yıllık izin isteği ve nedeni | Yalnızca yıllık ücretli izin; başka izin türü yok |
| Durum (`status`) | Talebin durumu: `Beklemede` · `Onaylandi` · `Reddedildi` | Veri değeridir: ASCII yazılır, Türkçe karakterli hali (`Onaylandı`) **farklı** bir değerdir |
| Kıdem (`seniority`) | Personelin hizmet süresi, tam yıl olarak | Bugün kod yalnızca yıl farkını alıyor (BR-2) |
| Hak (`entitlement`) | Kıdeme göre bir yıl için hak edilen izin günü | "Kalan" ile karıştırılmamalı |
| İzin günü | Bir talebin bakiyeden düşen gün sayısı; tam sayı | Takvim günü ≠ iş günü (BR-3) |
| Kullanılan (`used`) | `Onaylandi` durumundaki taleplerin izin günü toplamı | Bekleyenler dahil değil |
| Kalan / Bakiye (`remaining`) | Hak − Kullanılan | Tek bir yerde hesaplanır (invariant) |
| Devreden izin (`carry`) | Yıl sonunda bir sonraki yıla aktarılan kalan izin | Bugün uygulanmıyor; kod yorum satırında (OD-6) |

## Business rules

- **BR-1 Hak (md. 53):** kıdem < 1 yıl → 0 · 1–5 yıl (5 dahil) → 14 · 5'ten fazla ve 15'ten az
  → 20 · 15 yıl ve üzeri → 26 gün.
  *Mevcut kod:* 1–5 → 14 (doğru; koddaki "15 gün" yorumu yanlış) · 6–15 → 20 · 16+ → 26.
  **Tam 15 yıl kıdem kodda 20 gün, kanunda 26 gün** [IK onayı bekliyor].
- **BR-2 Kıdem:** tamamlanmış hizmet yılıdır (işe giriş yıl dönümü geçilince artar)
  [IK onayı bekliyor]. *Mevcut kod:* `bugün.yıl − giriş.yıl` (ay ve gün yok sayılıyor).
- **BR-3 İzin günü (md. 56):** izne denk gelen hafta tatili ve genel tatil günleri izinden
  sayılmaz [IK onayı bekliyor]. *Mevcut kod:* `(bitiş − başlangıç) + 1` takvim günü; koddaki
  "iş günü hesabı" yorumu yanlış.
- **BR-4 Kullanılan:** yalnızca `Onaylandi` durumundaki taleplerin izin günleri toplanır.
- **BR-5 Kalan:** Hak − Kullanılan. Bekleyen talepler düşülmez (*mevcut kod*; OD-3).
- **BR-6 Bakiye kontrolü:** talep, Kalan ≥ talebin izin günü ise oluşturulur; bakiyeyi tam
  kullanan talep kabul edilir (karar: İbrahim Gürhan, IK adına, 2026-11-04; spec 0008). Karar
  yalnızca domain'de verilir. Kalan yetmezse talep oluşmaz ve kullanıcı kalanı ve talep edilen
  günü söyleyen bir mesaj görür.
- **BR-7** Yeni talep her zaman `Beklemede` durumuyla oluşur.
- **BR-8** Geçmiş tarihli talep kabul edilir (IK geriye dönük giriş yapıyor; *mevcut kod*, korunur).
- **BR-9** Bitiş tarihi ≥ başlangıç tarihi. Talep oluşturulurken uygulanır (spec 0008); ters
  tarihli talep oluşmaz ve kullanıcı mesaj görür. Gün sayısı hesabı (`calc_days`) ters aralıkta
  hâlâ 0 ya da negatif döner (*mevcut kod*), ama bu değer artık bir talebe ulaşmıyor.

## Key domain invariants
- Kalan bakiye tek bir domain fonksiyonunda hesaplanır; web katmanı kendi hesabını yapmaz.
- Durum yalnızca `Beklemede`, `Onaylandi`, `Reddedildi` değerlerinden biri olabilir.
- Her izin talebi var olan bir personele bağlıdır.
- Bir işlem başarısız olduysa kullanıcıya başarılı gibi gösterilmez. Talep oluşturmada spec
  0008'den beri uygulanıyor: iş kuralı ihlali domain'de tipli bir istisnadır, web onu Türkçe
  bir mesaja çevirir.

## Open decisions
Her biri IK/ürün sahibinin kararını bekler. Karar verilince `/change` (davranış değişikliği) veya
`/fix-bug` (anlaşılan kuraldan sapma) ile ele alınır.
- **OD-1** Tam 15 yıl kıdem: 20 mi 26 mı? (BR-1) — öneri: 26, kanun gereği.
- **OD-2** Kıdem tam yıl mı, yıl farkı mı? (BR-2) — öneri: tam yıl. 29 Şubat'ta işe girenlerin yıl
  dönümü artık olmayan yıllarda 28 Şubat mı 1 Mart mı sayılacak?
- **OD-3** Bekleyen talepler Kalan'dan düşülsün mü? ("2018, karar yok") — öneri: yeni talepte
  kontrol için düşülsün, bakiye ekranında ayrı sütunda gösterilsin.
- **OD-4** İzin günü takvim günü mü, iş günü mü? Hafta tatili hangi gün(ler)? Resmî tatil
  takvimi nereden gelecek? (BR-3) — öneri: iş günü, Cumartesi+Pazar hafta tatili, tatil listesi
  yıllık IK girişi.
- **OD-5** 18 yaş ve altı ile 50 yaş ve üstü için en az 20 gün kuralı (md. 53) — doğum tarihi
  tutulmuyor. Öneri: kapsama alınsın, ayrı spec.
- **OD-6** Devreden izin (yorum satırındaki "en fazla 5 gün" taslağı) — öneri: IK yazılı kural
  verene kadar kapsam dışı; ölü kod refactor ile silinsin.
- **OD-7** Onay/red akışı yok; durum yalnızca seed verisinde değişiyor. Kim onaylar (Yönetici mi,
  IK mi)? — öneri: auth feature'ıyla birlikte ayrı spec.
- **OD-8** Kalıcılık: bellekteki veri her yeniden başlatmada kayboluyor. Öneri: SQLite, ADR ile.
