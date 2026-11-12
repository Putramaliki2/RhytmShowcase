# Menjalankan RhythmShowcase

## Prasyarat

- Python 3.10 atau lebih baru (tanpa package pihak ketiga).
- Windows PowerShell, Terminal macOS, atau shell Linux.

## Menjalankan aplikasi

Buka terminal pada folder project, lalu jalankan:

```powershell
python .\server\app.py --host 127.0.0.1 --port 8765
```

Buka [http://127.0.0.1:8765/](http://127.0.0.1:8765/) di browser. Database
SQLite dibuat otomatis di `data/rhythmshowcase.sqlite3`. Tekan `Ctrl+C` pada
terminal untuk menghentikan server.

Untuk memakai lokasi database lain:

```powershell
python .\server\app.py --host 127.0.0.1 --port 8765 --database .\data\demo.sqlite3
```

Server mencetak akun admin development awal:

- Email: `admin@rhythmshowcase.local`
- Kata sandi: `ChangeMe123!`

Untuk database baru, kredensial admin awal dapat diatur melalui environment
variable `RHYTHM_ADMIN_EMAIL` dan `RHYTHM_ADMIN_PASSWORD` sebelum server
dijalankan. Nilai ini dipakai saat akun admin pertama kali dibuat; perubahan
environment variable tidak mengubah akun yang sudah tersimpan. Akun awal ini
hanya untuk demo lokal.

## Menjalankan semua unit test

Pada terminal kedua, dari folder project:

```powershell
python -m unittest discover -s .\tests -v
```

Hasil verifikasi terakhir: **25 tests, OK**. Lima modul test ada di folder
`tests/`: autentikasi, katalog, ulasan komunitas, review editorial admin, dan
fitur admin.

Pemeriksaan sintaks tambahan:

```powershell
python -m py_compile .\server\app.py
node --check .\assets\app.js
```

## Alur demo manual

1. Buka `/` dan lihat kartu lagu yang diambil dari SQLite.
2. Buka `/user/catalog.html`; coba pencarian, game, tingkat kesulitan, dan
   rentang BPM. Pilih lagu untuk melihat halaman detail.
3. Daftar melalui `/user/register.html`, kemudian kirim ulasan bintang dan
   komentar pada halaman detail lagu. Setiap akun hanya dapat mengulas lagu
   yang sama satu kali.
4. Keluar dari sesi pengguna dengan tombol avatar, lalu masuk sebagai admin di
   `/admin/login.html`.
5. Buat review editorial sebagai draft, atau publikasikan dan konfirmasi.
   Coba ubah review, hapus review, nonaktifkan game, lalu simpan pengaturan.
6. Kembali ke detail lagu untuk memeriksa review editorial yang sudah tayang
   dan ulasan komunitas.

## Catatan cakupan

Ini adalah MVP demo lokal, bukan deployment produksi. Password awal admin,
SQLite lokal, dan HTTP tanpa TLS ditujukan untuk pengembangan lokal. Fitur
pengiriman email/notifikasi eksternal, upload media, reset password, dan
pengelolaan lagu oleh admin belum termasuk MVP.
