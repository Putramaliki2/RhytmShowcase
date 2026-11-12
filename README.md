# RhythmShowcase

Prototype website statis RhythmShowcase yang dibuat dengan HTML dan CSS tanpa framework atau backend.

## Menjalankan website

Pastikan Python sudah tersedia, lalu buka PowerShell di folder project dan jalankan:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Buka [http://127.0.0.1:8765/](http://127.0.0.1:8765/) di browser. Untuk menghentikan server, tekan `Ctrl+C` di PowerShell.

Tidak perlu memasang package tambahan.

## Struktur halaman

- `index.html` — mengarahkan ke beranda pengguna.
- `user/` — beranda, katalog, detail lagu, dan login pengguna.
- `admin/` — login admin, dashboard, editor review, game & lagu, pengaturan, dan halaman konfirmasi.
- `assets/styles.css` — styling bersama untuk seluruh halaman.

### URL halaman

| Halaman | URL lokal |
|---|---|
| Beranda | `/` |
| Login pengguna | `/user/login.html` |
| Katalog lagu | `/user/catalog.html` |
| Detail lagu | `/user/detail.html` |
| Login admin | `/admin/login.html` |
| Dashboard admin | `/admin/dashboard.html` |
| Tulis review | `/admin/review.html` |
| Game & lagu | `/admin/games.html` |
| Pengaturan admin | `/admin/settings.html` |
| Konfirmasi logout | `/admin/logout-warning.html` |
| Konfirmasi publikasi | `/admin/confirm-publish.html` |
| Konfirmasi hapus | `/admin/confirm-delete.html` |

Contoh URL lengkap: `http://127.0.0.1:8765/user/catalog.html`.

## Pemeriksaan halaman

Dengan server berjalan, jalankan perintah berikut di PowerShell kedua untuk memastikan semua halaman dan file CSS bisa diakses:

```powershell
$paths = @(
  "/",
  "/user/index.html",
  "/user/login.html",
  "/user/catalog.html",
  "/user/detail.html",
  "/admin/login.html",
  "/admin/dashboard.html",
  "/admin/review.html",
  "/admin/games.html",
  "/admin/settings.html",
  "/admin/logout-warning.html",
  "/admin/confirm-publish.html",
  "/admin/confirm-delete.html",
  "/assets/styles.css"
)

foreach ($path in $paths) {
  $response = Invoke-WebRequest -Uri "http://127.0.0.1:8765$path" -UseBasicParsing
  if ($response.StatusCode -ne 200) {
    throw "Gagal: $path mengembalikan HTTP $($response.StatusCode)"
  }
  Write-Host "OK $path"
}
```

## Checklist test browser

1. Buka `/`; pastikan diarahkan ke beranda RhythmShowcase.
2. Dari beranda, buka katalog lewat navigasi atau tombol **Lihat Semua**, lalu buka kartu lagu untuk melihat detail.
3. Buka login pengguna dari ikon akun, dan pastikan browser meminta email/kata sandi jika form kosong dikirim.
4. Di halaman login, gunakan **Jelajahi tanpa masuk** untuk kembali ke beranda.
5. Buka `/admin/login.html`, lalu ikuti tautan **Masuk sebagai Admin** dari login pengguna untuk memeriksa pemisahan halaman login.
6. Di dashboard admin, buka **Review Lagu**, **Game & Lagu**, dan **Pengaturan** melalui sidebar.
7. Dari halaman review, uji tautan **Publikasikan** dan **Kembali Mengedit** pada halaman konfirmasi.
8. Dari dashboard, uji **Hapus** dan tombol **Batal** pada halaman konfirmasi penghapusan.
9. Uji tautan **Logout**, tombol **Batal**, serta tombol **Ya, Logout**.
10. Ulangi pemeriksaan pada lebar mobile; konten seharusnya tetap muat tanpa overflow horizontal.

## Batasan prototype

Halaman dan navigasi dapat diperiksa secara lokal. Karena belum ada backend, login tidak memverifikasi akun, dan fitur simpan, pencarian, filter, publikasi, hapus, serta pengaturan belum menyimpan atau memproses data. Form login hanya menunjukkan validasi field wajib di browser.
