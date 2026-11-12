# Checklist MVP RhythmShowcase

Status pengujian: **unit test PASSED** (`python -m unittest discover -s .\tests
-v`: 25 tests, OK). Status manual ditandai hanya setelah alur tersebut
dijalankan; belum mengklaim hasil pemeriksaan browser sebagai unit test.

## Lima user story dan acceptance criteria

### MVP-1 — Registrasi, login, dan sesi ber-role

**User story:** Sebagai pengguna, saya ingin membuat akun, masuk, dan keluar
agar bisa berpartisipasi dengan akses yang sesuai.

- [x] Pengguna dapat mendaftar memakai email valid dan password minimal 8 karakter.
- [x] Email dinormalisasi, email duplikat/invalid ditolak, password disimpan
  sebagai salted PBKDF2 hash.
- [x] Login membuat sesi, logout mencabut sesi, dan akses user/admin dipisahkan.
- [x] Unit test: `tests/test_auth.py` — **PASSED**.

### MVP-2 — Menjelajahi dan mencari katalog lagu

**User story:** Sebagai pemain rhythm game, saya ingin mencari dan menyaring
lagu berdasarkan game, kesulitan, dan BPM agar mudah menemukan lagu yang cocok.

- [x] Katalog menampilkan lagu aktif dengan metadata game dan BPM.
- [x] Pencarian judul, artis, dan game dapat dikombinasikan dengan filter game,
  kesulitan, dan rentang BPM.
- [x] Rentang BPM tidak valid ditolak; game nonaktif tidak muncul di katalog.
- [x] Unit test: `tests/test_catalog.py` — **PASSED**.

### MVP-3 — Melihat detail dan mengirim ulasan komunitas

**User story:** Sebagai pengguna terdaftar, saya ingin membaca detail lagu dan
memberi rating/ulasan agar pengalaman bermain dapat dibagikan.

- [x] Detail lagu memuat metadata, review editorial yang sudah tayang, dan
  ulasan komunitas.
- [x] Pengguna login dapat memberi rating 1–5 dan komentar.
- [x] Rating/konten tidak valid, lagu tidak ditemukan, dan ulasan ganda ditolak.
- [x] Unit test: `tests/test_user_reviews.py` — **PASSED**.

### MVP-4 — Mengelola review editorial sebagai admin

**User story:** Sebagai admin, saya ingin membuat, mengedit, menerbitkan, dan
menghapus review editorial agar konten publik lagu tetap terkelola.

- [x] Admin dapat membuat dan mengedit review sebagai draft atau published.
- [x] Daftar review dapat difilter berdasarkan status dan review dapat dihapus.
- [x] Input review divalidasi dan hanya admin dapat mengelolanya.
- [x] Unit test: `tests/test_admin_reviews.py` — **PASSED**.

### MVP-5 — Dashboard, game, dan pengaturan admin

**User story:** Sebagai admin, saya ingin melihat ringkasan, mengelola game,
dan menyimpan preferensi agar operasional konten dapat dilakukan dari panel.

- [x] Dashboard menghitung total, published, draft, dan game aktif.
- [x] Admin dapat membuat/mengubah/mengaktifkan/nonaktifkan game; nama duplikat
  ditolak.
- [x] Pengaturan boolean yang dikenal dapat disimpan dan dibaca kembali; key
  yang tidak dikenal ditolak.
- [x] Unit test: `tests/test_admin_features.py` — **PASSED**.

## Ringkasan verifikasi

- [x] Seluruh 25 unit test pada lima file test lulus.
- [x] Backend lolos `python -m py_compile server/app.py`.
- [x] Frontend lolos `node --check assets/app.js`.
- [x] Smoke test browser lokal: registrasi/login user, kirim ulasan, login
  admin, buat/publikasi review, render detail, simpan pengaturan, dan CRUD
  status game.
- [x] Seluruh 14 rute halaman utama dan asset CSS merespons HTTP 200.
- [ ] Rekam/tinjau video demo end-to-end (`demo.mp4`).
- [ ] Uji tampilan lintas browser dan perangkat selain browser lokal yang
  digunakan saat verifikasi.

## Cakupan di luar MVP

Reset password via email, notifikasi eksternal, upload gambar/video, CRUD lagu,
dan deployment produksi belum diimplementasikan.
