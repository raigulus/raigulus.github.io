# Raigulus Saha Notları — 12 Eylül 2026

## Site envanteri (canlı: raigulus.github.io)
- Sitemap: 437 URL | Patch arşivi: 30 sayfa | Exotics DB: 74 sayfa
- Bugünkü loot: 2026-09-12 ok | Discord post: 2026-09-12 (manuel tetiklendi)
- GSC kotası dolu → 19 URL'lik kuyruk `GSC-QUEUE.txt`'de (repo kökü, commitlenmedi), kota açılınca 10+9 basılacak
- GSC gidişat: 11 gönderildi (parti1+vanguard), dark-hours kotaya takıldı, kalan 8 yarın

## Patch arşivi (tamamlandı, kronolojik)
2019: TU3 Dark Hours → TU4 Gunner → TU5/Ep1 → TU6/Ep2 → TU6.1 Snowball
2020: TU7/Ep3 → TU8 WONY → S1 Shadow Tide → TU9 → S2 Keener's → S3 Concealed → S4 End of Watch
2021-22: S5-S8 rerun tek sayfası → S9 Hidden Alliance → S10 Price of Power → S11 Reign of Fire
2023-24: Y5S1 Broken Wings → Y5S2 Puppeteers → Y5S3 Vanguard (+ Y6/Y7 mevcut)
- Kural: TU sayfası = sezona denk geliyorsa ayrı sayfa YOK (kopya olur)
- Yakalanan karışıklıklar: Countdown+Expertise S10 değil S9; Chameleon Shadow Tide değil Ep3

## Exotics denetimi (74 sayfa tarandı)
- 53 talent/mekanik hatası düzeltildi (Ouroboros, Iron Lung, Sacrum, Nemesis→Electromagnetic Accelerator, Bighorn→Big Game Hunter, vb.)
- 6 sayfa aklandı (Tardigrade, Waveform, Backfire, Investor, Loaded for Bear, Underboss)
- Patch loot tablolarından DB'ye 40 cross-link, 0 kırık
- Claws Out = named holster (egzotik değil) — hiçbir sayfaya bağlanmadı

## Otomasyonlar
- Loot penceresi 08:00 → 07:00 UTC'ye çekildi; Discord postu snapshot dönünce otomatik
- Sorun: Actions schedule 2 gündür uyuyor, manuel `gh workflow run "Update Guide Data"` ile çevrildi
- Öneri (bekliyor): loot workflow'una keepalive boş-commit

## Açık işler
1. GSC kuyruğu (kota açılınca)
2. Patch sayfalarına "Unofficial fan guide" disclaimer satırı (copyright kalkanı)
3. Ana sayfa hero zaten var ("Run it clean") — Discord bloğu zenginleştirildi

## İçerik temizliği (12 Eyl)
- Turkey/TRT geçen her yer silindi (lore hariç): loot + reset sayfaları, görünür metin + schema dahil

## Güvenlik taraması (temiz)
- Repoda token/yol/anahtar yok; token sadece GitHub Secrets'ta
- Script'lerdeki absolut path'ler Temp'te, repoda değil

## Discord işleri
- Davet: https://discord.gg/xj8jnS3Gkh (süresiz/limitsiz önerilir)
- Loot postu: schedule her koşuda `--post-discord` çalışır; snapshot `ok`'ye dönünce otomatik atar, `discord_loot_state.json` (`last_posted`) çift postu engeller
- 11-12 Eylül: schedule uyuduğu için 2 gün üst üste manuel tetiklendi, ikisi de tuttu
- Site tarafı: outbound linklerde `discord_click` takibi, Discord embed'lerinde `data-src` facade, ana sayfa Discord bloğu zenginleştirildi ("Find the squad for your next clear.")
