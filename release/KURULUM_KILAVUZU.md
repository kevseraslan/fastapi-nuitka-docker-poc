# FastAPI + Nuitka Standalone & Docker Dağıtım Kılavuzu

Bu kılavuz, **FastAPI + Nuitka + Docker PoC** projesini hedef bilgisayarda (Emre'nin çalışma ortamı) **hiçbir Python kaynak kodu (`.py` dosyaları) olmadan**, yalnızca derlenmiş Docker imajı ve orkestrasyon dosyaları ile sıfırdan kurup çalıştırmak için hazırlanmıştır.

---

## 1. Projenin Amacı ve Kaynak Kodsuz Dağıtım Mimarisi

Geleneksel Python backend dağıtımlarında `.py` kaynak kodları veya `.pyc` baytkod dosyaları sunucuya açık şekilde yüklenir. Bu durum, kaynak kodların kolaylıkla okunabilmesine ve tersine mühendisliğe açık hale gelmesine yol açar.

Bu PoC çalışmasında:
1. Python kaynak kodları **Nuitka Standalone Compiler** kullanılarak C diline dönüştürülmüş ve yerel Linux makine ikili dosyasına (`entry_build.bin` - ELF 64-bit) derlenmiştir.
2. Derlenen ikili dosya ve zorunlu çalışma zamanı kütüphaneleri **Multi-Stage Dockerfile** ile paketlenmiş, derleme araçları (`gcc`, `g++`, `patchelf`) ve Python kaynak kodları derleme aşamasında (Stage 1) bırakılmıştır.
3. Üretilen final runtime Docker imajı (`intellium-fastapi-poc-app:latest`), `docker save` ile bağımsız bir arşiv dosyası (`fastapi-nuitka-app.tar`) olarak paketlenmiştir.

> **Güvenlik Sınırları Notu:** Nuitka, Python kodunun düz metin olarak okunmasını ve standart Python decompilation araçlarıyla (uncompyle6 vb.) çözülmesini engeller; doğrudan kaynak kod görünürlüğünü %0 seviyesine indirir. Ancak herhangi bir C/C++ ikili dosyasında olduğu gibi, gelişmiş tersine mühendislik araçları (Ghidra, IDA Pro) ile assembly seviyesinde analiz teorik olarak mümkündür. Nuitka "mutlak ve aşılamaz bir kilit" değil, kurumsal düzeyde kaynak kod koruması sağlayan güçlü bir derleyicidir.

---

## 2. Hedef Bilgisayarda Gereken Önkoşullar ve Docker Kurulumu

Hedef bilgisayarda uygulamanın çalışması için **Python, pip, sanal ortam (venv), Nuitka veya C/C++ derleyicisi (GCC/MSVC) kesinlikle gerekmez**. Uygulama zaten makine koduna derlenmiş ve Docker konteyneri içine paketlenmiştir.

### Gereken Tek Yazılım:
- **Docker Desktop** (Windows / macOS) veya **Docker Engine + Docker Compose v2** (Linux)

### Windows İçin Docker Desktop Kurulum Adımları:
1. [Docker Resmi Web Sitesi](https://www.docker.com/products/docker-desktop/)'nden Docker Desktop for Windows installer dosyasını indirin ve kurun.
2. Kurulum sırasında **"Use WSL 2 instead of Hyper-V"** seçeneğinin işaretli olduğundan emin olun.
3. Bilgisayarı yeniden başlatın ve Docker Desktop uygulamasını açın.
4. Sol alt köşede yeşil renkte **"Engine running"** yazdığını doğrulayın.
5. Windows PowerShell terminalini açıp Docker motorunun hazır olduğunu kontrol edin:
   ```powershell
   docker info
   ```

---

## 3. Dağıtım Paketinin İçeriği (`release/`)

Emre'ye teslim edilen paket klasöründe yalnızca şu 4 dosya yer alır:

| Dosya Adı | Boyut | Açıklama |
| :--- | :---: | :--- |
| **`fastapi-nuitka-app.tar`** | ~102 MB | Nuitka ile derlenmiş Linux C ikili dosyasını barındıran, sıfır kaynak kodlu Docker imaj arşivi. |
| **`compose.yaml`** | ~2.2 KB | `build:` satırı içermeyen, doğrudan yüklenen imajı ve PostgreSQL 16 Alpine servisini çalıştıran Compose dosyası. |
| **`init.sql`** | ~1.4 KB | PostgreSQL ilk ayağa kalktığında tabloları (`users`, `refresh_tokens`, `alembic_version`) otomatik kuran SQL şeması. |
| **`.env.example`** | ~1.5 KB | Veritabanı parolası, portlar ve JWT anahtarlarını tanımlamak için hazırlanmış şablon dosya. |

---

## 4. Adım Adım Kurulum

Tüm komutları Windows PowerShell terminalinde, `release` klasörünün bulunduğu dizinde çalıştırınız:

```powershell
# Paket dizinine geçin
cd C:\Users\Emre\Desktop\release  # (Kendi klasör yolunuza göre güncelleyin)
```

### Adım 1: `.env` Dosyasının Oluşturulması

Docker Compose, veritabanı parolası ve JWT secret değerlerinin tanımlı olmasını zorunlu kılar. Şablon dosyayı kopyalayarak gerçek `.env` dosyanızı oluşturun:

```powershell
Copy-Item .env.example .env
```

Ardından `.env` dosyasını Not Defteri veya tercih ettiğiniz bir metin düzenleyiciyle açın ve güvenli parolalarınızı belirleyin:

```ini
# Host Port Eşlemeleri (Bilgisayarınızda çakışma varsa değiştirebilirsiniz)
HOST_APP_PORT=8000
HOST_DB_PORT=5433

# Veritabanı Yapılandırması
DB_HOST=localhost
DB_PORT=5433
DB_USER=postgres
DB_PASSWORD=GuvenceliParola123!
DB_NAME=py_fast_api_test

# JWT Güvenlik Anahtarları (Üretim ortamı için rastgele güçlü değerler girin)
JWT_SECRET=super_gizli_jwt_access_anahtari_2026_xyz
JWT_REFRESH_SECRET=super_gizli_jwt_refresh_anahtari_2026_abc
JWT_ISSUER=auth-service

# Sunucu Ayarları
HOST=0.0.0.0
PORT=8000
DEBUG=false
APP_NAME=FastAPI Nuitka PoC
ENVIRONMENT=production
ACCESS_EXPIRE_MIN=15
REFRESH_EXPIRE_DAYS=7
```

> **Önemli:** `compose.yaml` dosyası `${DB_PASSWORD:?DB_PASSWORD is required in .env}` kuralı içerir. `.env` dosyası eksikse veya parola boş bırakılırsa sistem güvenlik gerekçesiyle başlamaz.

---

### Adım 2: Docker İmajının Yüklenmesi (`docker load`)

Paket içindeki `fastapi-nuitka-app.tar` arşivini Docker motoruna aktarın:

```powershell
docker load -i fastapi-nuitka-app.tar
```

Komut tamamlandığında ekranda şu çıktıyı görmelisiniz:
```text
Loaded image: intellium-fastapi-poc-app:latest
```

İmajın başarıyla yüklendiğini doğrulamak için:
```powershell
docker images intellium-fastapi-poc-app:latest
```

---

### Adım 3: Servislerin Başlatılması (`docker compose up -d`)

Uygulamayı ve PostgreSQL veritabanını arka planda başlatmak için:

```powershell
docker compose up -d
```

Compose dosyası sırasıyla:
1. `prod_postgres_data` kalıcı Docker volume'ünü oluşturur.
2. PostgreSQL 16 Alpine konteynerini (`poc_prod_db`) başlatır.
3. Konteyner içindeki healthcheck'in `healthy` durumuna geçmesini bekler.
4. Derlenmiş FastAPI uygulamasını (`poc_prod_app`) ayağa kaldırır.

---

## 5. Veritabanının Otomatik Kurulumu (`init.sql`)

Hedef bilgisayarda Python ve Alembic kurulu olmadığı için veritabanı tablolarının oluşturulması Docker'ın yerleşik başlatma mekanizmasıyla çözülmüştür:

- `compose.yaml` dosyasında `./init.sql` dosyası PostgreSQL konteynerinin `/docker-entrypoint-initdb.d/init.sql` dizinine salt-okunur (`:ro`) olarak bağlanmıştır.
- PostgreSQL motoru ilk ayağa kalktığında bu betiği otomatik çalıştırarak `users`, `refresh_tokens` ve `alembic_version` tablolarını eksiksiz oluşturur.

> **Önemli Kural:** `init.sql` mekanizması **yalnızca veritabanı volume'ü tamamen boşken (ilk kurulumda)** bir kez çalışır. Eğer daha önceden kalma bir veri hacmi varsa PostgreSQL bu adımı atlar.

---

## 6. Kurulum Doğrulaması ve Sağlık Kontrolleri

### 1. Konteyner Durumlarını İnceleme:
```powershell
docker compose ps
```
Beklenen çıktı:
```text
NAME           IMAGE                              STATUS                   PORTS
poc_prod_db    postgres:16-alpine                 Up (healthy)             0.0.0.0:5433->5432/tcp
poc_prod_app   intellium-fastapi-poc-app:latest   Up                       0.0.0.0:8000->8000/tcp
```

### 2. Canlı Logları İnceleme:
```powershell
docker compose logs app
```
Beklenen log satırları:
```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Health Check Sorgusu:
PowerShell üzerinden:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```
Beklenen JSON yanıtı:
```json
{
  "status": "healthy"
}
```

### 4. Swagger UI Dokümantasyonuna Erişim:
Web tarayıcınızdan şu adrese gidin:
**`http://localhost:8000/docs`**

---

## 7. API Test Senaryoları (Swagger UI Üzerinden)

Sistemin tam fonksiyonel çalıştığını doğrulamak için `http://localhost:8000/docs` arayüzü üzerinden aşağıdaki adımları sırayla test edin:

### Test 1: Şifre Güvenlik Politikası Testi (Hatalı Şifre)
- **Endpoint:** `POST /api/register/`
- **Request Body:**
  ```json
  {
    "email": "test_hata@example.com",
    "password": "kisa1"
  }
  ```
- **Beklenen Durum:** `400 Bad Request`
- **Mesaj:** Şifrenin en az 8 karakter olması, büyük harf, rakam ve özel karakter içermesi gerektiğine dair hata döner.

### Test 2: Başarılı Kullanıcı Kaydı
- **Endpoint:** `POST /api/register/`
- **Request Body:**
  ```json
  {
    "email": "emre@example.com",
    "password": "GuvenliParola123!"
  }
  ```
- **Beklenen Durum:** `201 Created`
- **Dönen Değer:** `user_id`, `access_token`, `refresh_token`.

### Test 3: Başarılı Kullanıcı Girişi
- **Endpoint:** `POST /api/login/`
- **Request Body:**
  ```json
  {
    "email": "emre@example.com",
    "password": "GuvenliParola123!"
  }
  ```
- **Beklenen Durum:** `201 Created`
- **Dönen Değer:** Yeni `access_token` ve `refresh_token`.

### Test 4: Yetkili Dashboard Erişimi
- Swagger sayfasının sağ üstündeki yeşil **"Authorize"** butonuna tıklayın.
- Login yanıtında aldığınız `access_token` değerini yapıştırın ve yetkilendirin.
- **Endpoint:** `GET /api/dashboard/` → **Execute**
- **Beklenen Durum:** `200 OK`

---

## 8. Sık Karşılaşılan Sorunlar ve Çözümleri

### 1. "failed to connect to docker API" Hatası
- **Sebep:** Docker Desktop çalışmıyor veya motor henüz hazır değil.
- **Çözüm:** Docker Desktop uygulamasını açın ve sol altta "Engine running" görünene kadar bekleyin.

### 2. "port is already allocated" (Port Çakışması)
- **Sebep:** Bilgisayarınızda `8000` (FastAPI) veya `5433` (PostgreSQL) portunu kullanan başka bir uygulama var.
- **Çözüm:** `.env` dosyasını açın ve host portlarını boş olan bir porta yönlendirin:
  ```ini
  HOST_APP_PORT=8080
  HOST_DB_PORT=5435
  ```
  Ardından `docker compose up -d` komutunu tekrar çalıştırın.

### 3. "variable is required in .env" Hatası
- **Sebep:** `.env` dosyası oluşturulmamış veya zorunlu değişkenler boş bırakılmış.
- **Çözüm:** `Copy-Item .env.example .env` komutunu uygulayın ve dosya içindeki `DB_PASSWORD`, `JWT_SECRET` değerlerini doldurun.

### 4. "pull access denied for intellium-fastapi-poc-app" Hatası
- **Sebep:** `docker load` komutu çalıştırılmadan `docker compose up -d` denendiğinde Docker imajı internette arar ve bulamaz.
- **Çözüm:** Önce `docker load -i fastapi-nuitka-app.tar` komutunu çalıştırarak yerel imajı yükleyin.

### 5. FastAPI "database connection failed" Hatası
- **Sebep:** PostgreSQL henüz başlangıç adımlarını tamamlamadan FastAPI sorgu atmaya çalışmış olabilir.
- **Çözüm:** `compose.yaml` dosyasında healthcheck entegrasyonu bulunmaktadır (`condition: service_healthy`). `docker compose logs db` ile veritabanının hazır olduğunu teyit edin.

---

## 9. Sistemin Durdurulması ve Yeniden Başlatılması

### Sistemi Güvenli Şekilde Durdurma:
Veritabanı verilerini kaybetmeden konteynerleri durdurmak için:
```powershell
docker compose stop
```

### Durdurulan Sistemi Tekrar Başlatma:
```powershell
docker compose start
```

### Konteynerleri Tamamen Kapatıp Kaldırma (Verileri Koruyarak):
```powershell
docker compose down
```
> **Önemli:** Verilerinizi korumak için `docker compose down -v` komutunu **kullanmayınız**. `-v` parametresi veritabanı kalıcı volume'ünü siler.

---

## 10. Özet

Bu kılavuz sayesinde hedef ortamda:
- Hiçbir Python derleyicisi veya sanal ortam kurulmadan,
- Sıfır Python kaynak kodu (`.py`) erişimiyle,
- Yalnızca Docker araçları kullanılarak production düzeyinde çalışan bir FastAPI + PostgreSQL servisi ayağa kaldırılmış olmaktadır.
