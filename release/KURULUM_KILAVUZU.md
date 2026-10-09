# FastAPI + Nuitka Standalone & Docker Dağıtım Kılavuzu

Bu kılavuz, **FastAPI + Nuitka + Docker PoC** projesini hedef bilgisayarda (Emre'nin çalışma ortamı) **hiçbir Python kaynak kodu (`.py` dosyaları) olmadan**, yalnızca GitHub üzerinden indirilen `release/` klasöründeki derlenmiş Docker imajı ve orkestrasyon dosyaları ile sıfırdan kurup çalıştırmayı ve doğrulamayı hedefler.

---

## 1. Projenin Amacı ve Kaynak Kodsuz Dağıtım Mimarisi

Geleneksel Python dağıtımlarında `.py` kaynak kodları veya `.pyc` baytkod dosyaları sunucuya düz metin/kolay decompile edilebilir formatta aktarılır. Bu durum, kaynak kodların doğrudan okunabilmesine ve fikri mülkiyetin ifşasına zemin hazırlar.

Bu PoC mimarisinde:
1. Python kaynak kodları **Nuitka Standalone Compiler** aracılığıyla doğrudan C diline dönüştürülmüş ve yerel makine koduna (`entry_build.bin` - Linux ELF 64-bit) derlenmiştir.
2. Derlenen ikili dosya ve zorunlu sistem kütüphaneleri **Multi-Stage Dockerfile** ile paketlenmiş; derleyiciler (`gcc`, `g++`, `patchelf`) ve Python kaynak kodları derleme aşamasında (Stage 1) bırakılmıştır.
3. Üretilen final runtime Docker imajı (`intellium-fastapi-poc-app:latest`), `docker save` ile bağımsız bir arşiv (`fastapi-nuitka-app.tar`) olarak dışa aktarılmıştır.

> **Güvenlik Sınırları ve Gerçekçi Değerlendirme:**  
> Nuitka, Python kodunun düz metin olarak okunmasını ve standart Python decompilation araçlarıyla (uncompyle6, pycdc vb.) kaynak koda geri döndürülmesini engeller. Doğrudan kaynak kod görünürlüğünü ortadan kaldırır. Ancak tüm C/C++ ikili dosyalarında olduğu gibi, yetkin tersine mühendisler tarafından gelişmiş araçlarla (Ghidra, IDA Pro) assembly seviyesinde statik ve dinamik analiz yapılması teorik olarak mümkündür. Nuitka "kırılamaz mutlak bir kilit" değil; kurumsal dağıtımlarda kod hırsızlığını ve zahmetsiz kod incelemesini zorlaştıran etkili bir koruma katmanıdır.

---

## 2. Emre'nin Bilgisayarında Bulunması Gereken Önkoşullar

Emre'nin bilgisayarında **Python, pip, sanal ortam (venv), Nuitka veya C derleyicisi (GCC/MSVC) kesinlikle gerekmez**. Uygulama zaten makine koduna derlenmiş ve Docker konteynerine paketlenmiştir.

### Gereken Yazılımlar:
1. **Git & Git LFS:**  
   Büyük dosya (~102 MB imaj arşivi) takibi yapıldığı için Git LFS gereklidir.
   - [Git İndirme Sayfası](https://git-scm.com/download/win)
   - PowerShell üzerinden Git LFS durumunu doğrulayın:
     ```powershell
     git lfs version
     ```
2. **Docker Desktop:**  
   - [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) indirilip kurulmalıdır.
   - Kurulumda **"Use WSL 2 instead of Hyper-V"** seçeneği işaretlenmelidir.
   - Docker Desktop çalıştırılmalı ve sol altta yeşil **"Engine running"** ibaresi görülmelidir.
   - PowerShell üzerinden Docker kontrolü:
     ```powershell
     docker info
     ```

---

## 3. Repoyu Klonlama ve Dağıtım Paketinin İçeriği

### Repoyu Klonlama (Git LFS ile)
Windows PowerShell terminalinde aşağıdaki komutları sırasıyla çalıştırın:

```powershell
# 1. Repoyu klonlayın
git clone https://github.com/kevseraslan/fastapi-nuitka-docker-poc.git

# 2. Repo dizinine geçin
cd fastapi-nuitka-docker-poc

# 3. Git LFS dosyasını (büyük imaj arşivini) çekin
git lfs pull
```

### Yalnızca `release/` Klasörünün Kullanılması
> **Önemli İlke:** Emre kurulum sırasında ana depodaki geliştirici dosyalarına (`main.py`, `Dockerfile`, `requirements.txt` vb.) **kesinlikle ihtiyaç duymaz**. Kurulum adımları yalnızca `release/` klasörü içerisinden yürütülmelidir.

```powershell
cd release
```

`release/` klasörü toplam **5 dosyadan** oluşmaktadır:

| Dosya Adı | Boyut | Açıklama |
| :--- | :---: | :--- |
| **`fastapi-nuitka-app.tar`** | ~102 MB | Nuitka ile derlenmiş Linux C ikili dosyasını barındıran, sıfır kaynak kodlu Docker imaj arşivi. |
| **`compose.yaml`** | ~2.2 KB | `build:` satırı içermeyen, doğrudan yüklenen imajı ve PostgreSQL 16 Alpine servisini çalıştıran Compose dosyası. |
| **`init.sql`** | ~1.4 KB | PostgreSQL ilk ayağa kalktığında tabloları (`users`, `refresh_tokens`, `alembic_version`) otomatik kuran SQL şeması. |
| **`.env.example`** | ~1.5 KB | Veritabanı parolası, portlar ve JWT anahtarlarını tanımlamak için hazırlanmış şablon dosya. |
| **`KURULUM_KILAVUZU.md`** | ~12 KB | Bu adım adım kurulum ve doğrulama rehberi. |

---

## 4. Adım Adım Kurulum

Terminalde `release` klasöründe olduğunuzdan emin olun (`pwd` komutu ile kontrol edebilirsiniz).

### Adım 1: `.env` Dosyasının Oluşturulması ve Yapılandırma

Docker Compose, veritabanı parolası ve JWT secret değerlerinin tanımlı olmasını zorunlu kılar. Şablon dosyayı kopyalayarak gerçek `.env` dosyanızı oluşturun:

```powershell
Copy-Item .env.example .env
```

`.env` dosyasını Not Defteri ile açarak kendi ortamınıza göre güncelleyin:

```ini
# Host Port Eşlemeleri (Bilgisayarınızda çakışma varsa host portlarını değiştirebilirsiniz)
HOST_APP_PORT=8000
HOST_DB_PORT=5433

# Veritabanı Yapılandırması (Konteyner içi bağlantılar compose.yaml tarafından yönetilir)
DB_HOST=localhost
DB_PORT=5433
DB_USER=postgres
DB_PASSWORD=GuvenceliParola123!
DB_NAME=py_fast_api_test

# JWT Güvenlik Anahtarları
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

> **Ağ Mimarisi Notu:**  
> `compose.yaml` içerisinde FastAPI konteyneri PostgreSQL konteynerine Docker dahili ağı (`bridge`) üzerinden `db:5432` adresiyle bağlanır (`ASYNC_DATABASE_URL` ve `SYNC_DATABASE_URL` tanımları `compose.yaml` içinde otomatik olarak `@db:5432/` şeklinde ayarlanmıştır). `.env` içindeki `HOST_DB_PORT=5433`, veritabanına dışarıdan (host bilgisayarınızdan veya DBeaver/pgAdmin gibi araçlardan) erişebilmeniz için dışarıya açılan porttur.

---

### Adım 2: Docker İmajının Yüklenmesi (`docker load`)

Paket içindeki `fastapi-nuitka-app.tar` arşivini yerel Docker motoruna yükleyin:

```powershell
docker load -i fastapi-nuitka-app.tar
```

Beklenen çıktı:
```text
Loaded image: intellium-fastapi-poc-app:latest
```

İmajın yüklendiğini teyit etmek için:
```powershell
docker images intellium-fastapi-poc-app:latest
```

---

### Adım 3: Servislerin Başlatılması (`docker compose up -d`)

PostgreSQL ve FastAPI konteynerlerini arka planda başlatın:

```powershell
docker compose up -d
```

Compose dosyası sırasıyla:
1. `poc_prod_postgres_data` kalıcı Docker volume'ünü oluşturur.
2. PostgreSQL 16 Alpine konteynerini (`poc_prod_db`) başlatır.
3. Konteyner içindeki healthcheck'in `healthy` durumuna geçmesini bekler.
4. Derlenmiş FastAPI uygulamasını (`poc_prod_app`) ayağa kaldırır.

---

## 5. Veritabanının Otomatik Kurulumu (`init.sql`)

Hedef bilgisayarda Python ve Alembic kurulu olmadığı için tablolar Docker'ın yerleşik başlatma mekanizmasıyla oluşturulur:

- `compose.yaml` dosyasında `./init.sql` dosyası PostgreSQL konteynerinin `/docker-entrypoint-initdb.d/init.sql` dizinine bağlanmıştır.
- PostgreSQL motoru ilk ayağa kalktığında bu betiği çalıştırarak `users`, `refresh_tokens` ve `alembic_version` tablolarını oluşturur.

> **Önemli Kural:** `init.sql` mekanizması **yalnızca veritabanı volume'ü tamamen boşken (ilk kurulumda)** çalışır. Eğer daha önceden kalma bir veri hacmi varsa PostgreSQL bu adımı çalıştırmaz.

---

## 6. Kurulum Doğrulaması ve Sağlık Kontrolleri

### 1. Konteyner Durumlarını İnceleme:
```powershell
docker compose ps
```
Beklenen durum:
```text
NAME           IMAGE                              STATUS                   PORTS
poc_prod_db    postgres:16-alpine                 Up (healthy)             0.0.0.0:5433->5432/tcp
poc_prod_app   intellium-fastapi-poc-app:latest   Up                       0.0.0.0:8000->8000/tcp
```

### 2. Canlı Logları İnceleme:
```powershell
docker compose logs app
```
Beklenen log çıktısı:
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
Beklenen yanıt:
```json
{
  "status": "healthy"
}
```

### 4. Swagger UI Dokümantasyonuna Erişim:
Web tarayıcınızdan şu adrese gidin:
**`http://localhost:8000/docs`**

---

## 7. API Test Senaryoları (Swagger UI / Docs Üzerinden)

Tarayıcınızda `http://localhost:8000/docs` adresini açarak aşağıdaki senaryoları sırayla test edin:

### Test 1: Şifre Politikası İhlali (Hatalı Şifre)
- **Endpoint:** `POST /api/register/` → **Try it out**
- **Request Body:**
  ```json
  {
    "email": "test_hata@example.com",
    "password": "kisa1"
  }
  ```
- **Execute** butonuna tıklayın.
- **Beklenen HTTP Kodu:** `400 Bad Request`
- **Beklenen Yanıt:** Şifrenin en az 8 karakter olması, büyük harf, rakam ve özel karakter içermesi gerektiğine dair hata döner.

### Test 2: Başarılı Kullanıcı Kaydı
- **Endpoint:** `POST /api/register/` → **Try it out**
- **Request Body:**
  ```json
  {
    "email": "emre@example.com",
    "password": "GuvenliParola123!"
  }
  ```
- **Execute** butonuna tıklayın.
- **Beklenen HTTP Kodu:** `201 Created`
- **Beklenen Alanlar:**
  ```json
  {
    "user_id": 1,
    "access_token": "eyJhbGciOi...",
    "refresh_token": "..."
  }
  ```

### Test 3: Başarılı Kullanıcı Girişi
- **Endpoint:** `POST /api/login/` → **Try it out**
- **Request Body:**
  ```json
  {
    "email": "emre@example.com",
    "password": "GuvenliParola123!"
  }
  ```
- **Execute** butonuna tıklayın.
- **Beklenen HTTP Kodu:** `201 Created`
- **Beklenen Alanlar:** `access_token`, `refresh_token`, `user_id`. `access_token` değerini kopyalayın.

### Test 4: Yetkili Dashboard Erişimi
Uygulamada Dashboard endpoint'i Bearer JWT token'ı doğrulamaktadır:
- **Swagger Sayfasında:** `GET /api/dashboard/` endpoint'ini açın.
- Endpoint parametrelerinde yer alan **`Authorization`** header alanına:
  ```text
  Bearer <kopyaladığınız_access_token>
  ```
  (veya `access_token` query parametresi alanına yalnızca token'ı) yazın.
- **Execute** butonuna tıklayın.
- **Beklenen HTTP Kodu:** `200 OK`
- **Beklenen Yanıt:**
  ```json
  {
    "user_id": 1,
    "refresh_token": "..."
  }
  ```

---

## 8. Sık Karşılaşılan Sorunlar ve Çözümleri

### 1. `git lfs pull` Yapılmadan İmaj Yüklenmeye Çalışılırsa
- **Belirti:** `docker load` komutu `invalid tar header` veya `archive/tar: invalid tar header` hatası verir.
- **Sebep:** Git LFS kurulu olmadan sadece pointer dosyası (130 baytlık metin) indirilmiştir.
- **Çözüm:** `git lfs install` ve ardından `git lfs pull` çalıştırarak gerçek ~102 MB'lık dosyanın indiğinden emin olun (`Get-Item fastapi-nuitka-app.tar` ile boyutu kontrol edin).

### 2. "failed to connect to docker API" Hatası
- **Sebep:** Docker Desktop çalışmıyor veya motor henüz hazır değil.
- **Çözüm:** Docker Desktop uygulamasını açın ve sol altta "Engine running" görünene kadar bekleyin.

### 3. "port is already allocated" (Port Çakışması)
- **Sebep:** Bilgisayarınızda `8000` (FastAPI) veya `5433` (PostgreSQL) portunu kullanan başka bir servis var.
- **Çözüm:** `release/.env` dosyasını açarak host portlarını boş bir porta yönlendirin:
  ```ini
  HOST_APP_PORT=8080
  HOST_DB_PORT=5435
  ```
  Ardından `docker compose up -d` komutunu tekrar çalıştırın.

### 4. "variable is required in .env" Hatası
- **Sebep:** `.env` dosyası oluşturulmamış veya `DB_PASSWORD`, `JWT_SECRET` değerleri boş bırakılmış.
- **Çözüm:** `Copy-Item .env.example .env` komutunu uygulayın ve zorunlu alanları doldurun.

### 5. FastAPI "database connection failed" Hatası
- **Sebep:** PostgreSQL konteyneri henüz ayağa kalkmadan uygulamanın istek alması.
- **Çözüm:** `compose.yaml` dosyasında healthcheck entegrasyonu bulunmaktadır (`condition: service_healthy`). `docker compose logs db` komutuyla veritabanının sağlıklı çalıştığını doğrulayın.

---

## 9. Sistemin Durdurulması ve Yeniden Başlatılması

### Sistemi Durdurma (Verileri Koruyarak):
```powershell
docker compose stop
```

### Durdurulan Sistemi Tekrar Başlatma:
```powershell
docker compose start
```

### Konteynerleri Kaldırma (Verileri Koruyarak):
```powershell
docker compose down
```
> **Önemli Güvenlik Uyarısı:** Verilerinizi korumak için `docker compose down -v` komutunu **kullanmayınız**. `-v` bayrağı kalıcı veritabanı volume'ünü siler.

---

## 10. Sonuç ve Doğrulama Hedefi

Bu kurulum kılavuzu, Emre'nin çalışma ortamında:
- Hiçbir Python derleyicisi veya sanal ortam kurulmadan,
- Sıfır `.py` kaynak kodu erişimiyle,
- Yalnızca Git LFS ve Docker Desktop kullanılarak Nuitka ile derlenmiş bir FastAPI backend servisinin başarıyla çalıştırılabileceğini ve doğrulanabileceğini göstermeyi hedefler.
