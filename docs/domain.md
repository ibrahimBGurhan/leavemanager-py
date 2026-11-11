# Domain

> Bootstrap'te (2026-10-23) dolduruldu. Kuralların referans kaynağı **4857 sayılı İş Kanunu
> md. 53 ve 56** ile güncel IK yönetmeliğidir. Kanundan türetilen ama henüz IK tarafından
> onaylanmamış kurallar **[IK onayı bekliyor]** ile işaretlidir. **Mevcut kod** satırları bugünkü
> davranışı anlatır; karakterizasyon testleri bunu sabitler, değişiklik `/change` ile yapılır.

## Ubiquitous language

| Term | Meaning | Notes / not to be confused with |
|---|---|---|
| Personel (`Employee`) | İzin hakkı olan çalışan: ad, birim, işe giriş tarihi | Kullanıcı hesabı değildir; bir hesap en fazla bir personele bağlanır (spec 0018) |
| Birim (`department`) | Personelin bağlı olduğu departman (IT, Muhasebe, IK, Satis…) | |
| İzin Talebi (`LeaveRequest`) | Bir personelin başlangıç–bitiş tarihli yıllık izin isteği ve nedeni | Yalnızca yıllık ücretli izin; başka izin türü yok |
| Durum (`status`) | Talebin durumu: `Beklemede` · `Onaylandi` · `Reddedildi` | Veri değeridir: ASCII yazılır, Türkçe karakterli hali (`Onaylandı`) **farklı** bir değerdir. Geçişler: BR-10 |
| Kıdem (`seniority`) | Personelin hizmet süresi, tam yıl olarak | Bugün kod yalnızca yıl farkını alıyor (BR-2) |
| Hak (`entitlement`) | Kıdeme göre bir yıl için hak edilen izin günü | "Kalan" ile karıştırılmamalı |
| İzin günü | Bir talebin bakiyeden düşen gün sayısı; tam sayı | İş günüdür: hafta sonu ve resmî tatil sayılmaz (BR-3) |
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
- **BR-3 İzin günü (md. 56):** izin günü iş günüdür: aralıktaki (başlangıç ve bitiş dahil)
  Pazartesi–Cuma günlerinden resmî tatil olmayanlar sayılır; Cumartesi ve Pazar hafta tatilidir
  (karar: İbrahim Gürhan, IK adına, 2026-11-05; spec 0014). Resmî tatiller 2026–2027 için kodda
  sabit listededir (`domain/workdays.py`: 1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz,
  30 Ağustos, 29 Ekim; Ramazan ve Kurban Bayramı günleri). Arife yarım günleri tam iş günü sayılır
  (OD-9). Liste dışındaki yıllarda yalnız hafta sonu düşülür (OD-10). Bakiye, Kullanılan,
  Bekleyen, onay ve Talepler ekranının "Gun" sütunu aynı hesabı kullanır.
- **BR-4 Kullanılan:** yalnızca `Onaylandi` durumundaki taleplerin izin günleri toplanır.
- **BR-5 Kalan ve Bekleyen:** Kalan = Hak − Kullanılan. Bekleyen = personelin `Beklemede`
  durumundaki taleplerinin izin günleri toplamı, tarihe bakılmaz (geçmiş tarihli de sayılır).
  `Reddedildi` hiçbir hesaba girmez. Bakiye tablosu Kalan'ı ve Bekleyen'i ayrı sütunlarda
  gösterir (karar: İbrahim Gürhan, IK adına, 2026-11-05; spec 0013, OD-3).
- **BR-6 Bakiye kontrolü:** yeni talep, Kalan − Bekleyen ≥ talebin izin günü ise oluşturulur
  (spec 0013); bakiyeyi tam kullanan talep kabul edilir (karar: İbrahim Gürhan, IK adına,
  2026-11-04; spec 0008). Karar yalnızca domain'de verilir. Yetmezse talep oluşmaz ve kullanıcı
  kalanı, bekleyeni ve talep edilen günü söyleyen bir mesaj görür. Kalan − Bekleyen sıfırın
  altındaysa (kural öncesi veri) özel durum yoktur: her talep reddedilir.
- **BR-7** Yeni talep her zaman `Beklemede` durumuyla oluşur.
- **BR-8** Geçmiş tarihli talep kabul edilir (IK geriye dönük giriş yapıyor; *mevcut kod*, korunur).
- **BR-9** Bitiş tarihi ≥ başlangıç tarihi. Talep oluşturulurken uygulanır (spec 0008); ters
  tarihli talep oluşmaz ve kullanıcı mesaj görür. Gün sayısı hesabı ters aralıkta 0 döner, ama bu
  değer bir talebe ulaşmaz. **İş günü içermeyen talep** (yalnız hafta sonu ve/veya resmî tatil)
  oluşmaz; kullanıcı "Seçilen tarihler arasında iş günü yok." mesajını görür (spec 0014). İhlal
  sırası: bozuk girdi → personel → tarih aralığı → iş günü yok → bakiye.
- **BR-10 Durum geçişleri** (spec 0010): bir talep yalnızca `Beklemede` iken sonuçlandırılır:
  `Beklemede → Onaylandi` ya da `Beklemede → Reddedildi`. `Onaylandi` ve `Reddedildi` son
  durumlardır; geri alınmaz, birbirine çevrilmez. Onayda bakiye yeniden kontrol edilir: Kalan ≥ talebin
  izin günü (aynı karar fonksiyonu; diğer bekleyen talepler sayılmaz, spec 0013 K-4); yetmezse talep `Beklemede` kalır. Redde bakiye kontrolü
  yoktur. Geçmiş tarihli bekleyen talep de sonuçlandırılabilir (BR-8). Sonuçlandıran IK (her
  talep, kendi talebi dahil) ya da birimin Yöneticisidir (birimindeki başka bir personelin talebi;
  spec 0021). Karar tek aşamalıdır; Personel sonuçlandıramaz (OD-7, `docs/security.md`).

- **BR-11 Personel kaydı** (spec 0022): yeni personeli yalnız IK ekler (`docs/security.md`).
  Ad (en fazla 100 karakter) ve birim (en fazla 50) zorunludur; baştaki ve sondaki boşluk atılır,
  kırpılınca boş kalan değer eksiktir; birimin harf büyüklüğü korunur (Yönetici birimi tam
  eşleşmeyle bulur, spec 0021). İşe giriş tarihi zorunludur, 1950-01-01'den önce olamaz; gelecek
  tarih kabul edilir (hak BR-1/BR-2 ile hesaplanır: henüz başlamamış personelin hakkı 0). Aynı ad
  ve birimle ikinci bir kayıt açılabilir; kayıtlar numarayla ayrılır. Numarayı depo verir:
  kayıtlı en büyük numaradan bir fazla (boş veritabanında 1), aynı anda gelen iki ekleme ayrı
  numara alır. İhlal sırası: ad → birim → tarih; ilk ihlal bildirilir, kayıt oluşmaz. Personeli
  düzenleme, silme ve pasife alma yoktur. Yeni Personel ekranındaki birim öneri listesi Türkçe
  alfabe sırasıyla gelir (spec 0028, `domain/collation.py`): harf sırası
  a b c ç d e f g ğ h ı i j k l m n o ö p q r s ş t u ü v w x y z (q, w, x Latin yerinde);
  büyük/küçük harf ayrılmaz, Türkçe kuralla (I ile ı, İ ile i aynı harftir; "IT", "İdari"den önce
  gelir); boşluk, noktalama ve rakam her harften önce, alfabe dışı harfler (é, ä…) z'den sonra
  gelir; yalnız harf büyüklüğüyle ayrılan birimlerde eşitlikte karakter kodu küçük olan önce gelir
  (genelde büyük harf önce; İ/i'de i önce, çünkü İ'nin karakter kodu büyüktür). Sıra sunucunun dil
  ayarına bağlı değildir.

## Key domain invariants
- Kalan bakiye tek bir domain fonksiyonunda hesaplanır; web katmanı kendi hesabını yapmaz.
- Durum yalnızca `Beklemede`, `Onaylandi`, `Reddedildi` değerlerinden biri olabilir.
- Her izin talebi var olan bir personele bağlıdır.
- Bir işlem başarısız olduysa kullanıcıya başarılı gibi gösterilmez. Talep oluşturmada spec
  0008'den beri uygulanıyor: iş kuralı ihlali domain'de tipli bir istisnadır, web onu Türkçe
  bir mesaja çevirir. Onay/red de aynı kuralla çalışır (spec 0010).

## Open decisions
Her biri IK/ürün sahibinin kararını bekler. Karar verilince `/change` (davranış değişikliği) veya
`/fix-bug` (anlaşılan kuraldan sapma) ile ele alınır.
- **OD-1** Tam 15 yıl kıdem: 20 mi 26 mı? (BR-1) — öneri: 26, kanun gereği.
- **OD-2** Kıdem tam yıl mı, yıl farkı mı? (BR-2) — öneri: tam yıl. 29 Şubat'ta işe girenlerin yıl
  dönümü artık olmayan yıllarda 28 Şubat mı 1 Mart mı sayılacak?
- **OD-3** ~~Bekleyen talepler Kalan'dan düşülsün mü?~~ — **kapandı** (spec 0013, İbrahim Gürhan,
  IK adına, 2026-11-05): yeni talep kontrolünde düşülür, bakiye tablosunda ayrı sütun; Kalan ve
  onay kontrolü değişmez (BR-5, BR-6, BR-10).
- **OD-4** ~~İzin günü takvim günü mü, iş günü mü?~~ — **kapandı** (spec 0014, İbrahim Gürhan,
  IK adına, 2026-11-05): iş günü; Cumartesi + Pazar hafta tatili; 2026–2027 resmî tatilleri kodda
  sabit liste (BR-3). IK'nın tatil girdiği ekran kalıcılık (OD-8) sonrası ayrı iş.
- **OD-5** 18 yaş ve altı ile 50 yaş ve üstü için en az 20 gün kuralı (md. 53) — doğum tarihi
  tutulmuyor. Öneri: kapsama alınsın, ayrı spec.
- **OD-6** Devreden izin (yorum satırındaki "en fazla 5 gün" taslağı) — öneri: IK yazılı kural
  verene kadar kapsam dışı; ölü kod refactor ile silinsin.
- **OD-7** ~~Onay/red akışı yok~~ — **kapandı** (spec 0010, İbrahim Gürhan, 2026-11-04): bu
  sürümde IK onaylar (BR-10). "Yalnızca IK" kısıtı spec 0020'de uygulandı; spec 0021 ile birimin
  Yöneticisi de birimindeki talepleri tek aşamada sonuçlandırır.
- **OD-8** ~~Kalıcılık: bellekteki veri her yeniden başlatmada kayboluyor.~~ — **karar verildi**
  (ADR-0001, İbrahim Gürhan, 2026-11-05): SQLite, standart kütüphane `sqlite3`, storage katmanının
  arkasında; üretimde demo verisi yüklenmez. Uygulandı (spec 0017).
- **OD-9** Arife yarım günleri (Ramazan ve Kurban Bayramı arifesi, 28 Ekim) bugün tam iş günü
  sayılıyor (spec 0014 K-3). Yarım gün sayılması kesirli bakiye ister — öneri: IK isterse ayrı
  spec.
- **OD-10** Resmî tatil listesi yalnız 2026–2027'yi kapsıyor; sonraki yıllarda yalnız hafta sonu
  düşülür (spec 0014 K-4). Öneri: 2027 sonundan önce liste güncellensin ya da IK girişi (OD-8
  sonrası) yapılsın.
