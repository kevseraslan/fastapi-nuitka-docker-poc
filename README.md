# FastAPI + Nuitka Standalone & Docker Multi-Stage PoC

Bu proje, Python ve FastAPI tabanlı backend servislerinin kaynak kodlarını (`.py` dosyaları) tersine mühendisliğe ve izinsiz kod erişimine karşı korumak amacıyla geliştirilmiş bir **Proof of Concept (PoC)** çalışmasıdır.

Python kaynak kodları **Nuitka Standalone Compiler** kullanılarak C diline dönüştürülüp yerel makine ikili dosyasına (`.bin` / `.exe`) derlenmekte, ardından **Multi-Stage Dockerfile** mimarisi sayesinde final üretim konteynerine **yalnızca derlenmiş C ikili dosyası** aktarılmaktadır. Bu sayede üretim ortamında çalışan imaj içerisinde hiçbir okunabilir `.py` kaynak kodu, geliştirme aracı veya derleyici paketi barındırılmaz.

---

## 🚀 Temel Özellikler ve Mimari

- **Katmanlı FastAPI Mimarisi:** Router, Service, Schema, Model ve Core katmanlarına ayrılmış RESTful API yapısı.
- **Güvenli Kimlik Doğrulama:** JWT Access & Refresh Token mekanizması, Bcrypt şifre hashleme ve 4 kurallı şifre güvenlik politikası (Min 8 karakter, büyük harf, rakam, özel karakter).
- **Nuitka Standalone Derlemesi:** Python kodunu C diline çevirip makine koduna dönüştürerek düz metin kaynak kod görünürlüğünü %0 seviyesine indiren derleme altyapısı.
- **Multi-Stage Dockerfile:**
  - **Stage 1 (Builder):** `gcc 12`, `g++`, `patchelf` ve Nuitka ile C derlemesini tamamlayan geçici derleme ortamı.
  - **Stage 2 (Runtime):** Yalnızca `/app/dist` altındaki Linux ELF ikili dosyasını (`entry_build.bin`) ve zorunlu paylaşımlı kütüphaneleri barındıran kaynak kodsuz minimal çalışma ortamı.
- **Docker Compose Entegrasyonu:** PostgreSQL 16 Alpine ve FastAPI konteynerlerinin izole ağda haberleştiği, healthcheck ve kalıcı volume destekli servis orkestrasyonu.
- **Alembic Veritabanı Göçleri:** Bağımsız veritabanı sürüm yönetimi.

---

## 📁 Proje Dizin Yapısı

```text
fastapi-nuitka-docker-poc/
├── alembic/              # Alembic veritabanı göç betikleri ve env.py
├── core/                 # Uygulama ayarları (Settings), middleware ve exception yapıları
├── models/               # SQLAlchemy ORM veritabanı modelleri (User, RefreshToken)
├── routers/              # API rotaları (/register, /login, /dashboard, /logout)
├── schemas/              # Pydantic veri doğrulama ve transfer şemaları
├── services/             # İş mantığı servisleri
├── .dockerignore         # Docker build bağlamı filtreleme kuralları
├── .env.example          # Güvenli ortam değişkenleri şablonu
├── .gitignore            # Git filtreleme kuralları
├── alembic.ini           # Alembic ana konfigürasyon dosyası
├── compose.yaml          # Docker Compose servis tanımı (PostgreSQL 16 + FastAPI)
├── database.py           # Veritabanı motoru ve oturum bağımlılığı
├── Dockerfile            # Multi-Stage Linux Nuitka derleme ve runtime dosyası
├── entry_build.py        # Nuitka derlemesi için bağımsız entrypoint sarmalayıcısı
├── main.py               # FastAPI ana uygulama başlangıcı
└── requirements.txt      # Python bağımlılıkları
```

---

## 🛠️ Kurulum ve Çalıştırma

### 1. Çevre Değişkenlerinin Hazırlanması

Kök dizinde yer alan `.env.example` dosyasını kopyalayarak `.env` dosyasını oluşturun:

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell / CMD)
copy .env.example .env
```

`.env` dosyası içerisindeki veritabanı parolasını ve JWT secret anahtarlarını kendi gereksinimlerinize göre belirleyin.

### 2. Docker Compose ile Başlatma

PostgreSQL ve Nuitka ile derlenen FastAPI uygulamasını başlatmak için:

```bash
# Konteynerleri derleyin ve arka planda çalıştırın
docker compose up -d --build
```

Servis durumunu ve logları kontrol etmek için:

```bash
docker compose ps
docker compose logs -f app
```

Uygulama ayağa kalktığında `http://localhost:8000/docs` üzerinden Swagger arayüzüne erişebilirsiniz.

### 3. Veritabanı Göçlerini (Alembic) Çalıştırma

Konteyner ilk kez ayağa kalktığında veritabanı tablolarını oluşturmak için:

```bash
# Yerel ortamdan Docker PostgreSQL portuna migration uygulama
alembic upgrade head
```

---

## 🔒 Güvenlik Notları

- Üretim ortamında çalışan Docker imajı içerisinde hiçbir `.py`, `.env` veya `.git` dosyası bulunmaz.
- Tüm sırlar `.env` üzerinden enjekte edilir; `compose.yaml` dosyasında varsayılan sabit şifre veya secret barındırılmaz.
- Nuitka, Python kodunu C makine koduna dönüştürerek doğrudan kod okunabilirliğini ve decompilation araçlarını engeller. Ancak çalışma zamanı environment değişkenleri ve veritabanı bağlantı güvenliği standart güvenlik ilkelerine (Secrets Manager, KMS vb.) uygun yönetilmelidir.
