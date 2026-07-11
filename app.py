import os
import asyncio
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from supabase import create_client, Client
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import uvicorn

# --- 1. SİBER GÜVENLİK VE GİZLİ ŞİFRELER ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

supabase: Client = None

# --- 2. BULUT BAĞLANTILARINI ATEŞLEME ---
try:
    if SUPABASE_URL and SUPABASE_KEY and GEMINI_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        genai.configure(api_key=GEMINI_KEY)
        print("✅ Bulut Kilitleri Açıldı! Otopilot Sistemi Devrede.")
    else:
        print("⚠️ KRİTİK UYARI: Gizli şifreler (Environment Variables) bulunamadı!")
except Exception as e:
    print(f"🔌 Bağlantı Hatası: {str(e)}")

# --- 3. OTOPİLOT: KENDİ KENDİNE EN GÜNCEL MODELİ SEÇEN AKILLI DÜĞÜM ---
def en_guncel_modeli_sec():
    """
    Google API'yi anlık tarayarak o an yayında olan en güncel,
    en hızlı ve metin analizine en uygun modeli kendi kendine bulur ve uygular.
    """
    try:
        aktif_modeller = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name.lower():
                    aktif_modeller.append(m.name)
        
        # Öncelik sıramız: En yeni nesilden başla (3.5 -> 3.1 -> 3 -> 2.5 -> 1.5)
        oncelik_listesi = ["3.5-flash", "3.1-flash", "3-flash", "2.5-flash", "1.5-flash"]
        for oncelik in oncelik_listesi:
            for model_adi in aktif_modeller:
                if oncelik in model_adi:
                    print(f"🤖 Otopilot Seçimi: En güncel model yakalandı ({model_adi})")
                    return model_adi
                    
        # Eğer özel eşleşme olmazsa Google'ın listesindeki ilk aktif modeli al
        if aktif_modeller:
            return aktif_modeller[0]
    except Exception as e:
        print(f"⚠️ Model taramada anlık hata, yedek motora geçiliyor: {e}")
        
    return "gemini-1.5-flash" # Her ihtimale karşı siber kalkan

app = FastAPI()

# --- 4. KUSURSUZ KULLANICI ARAYÜZÜ ---
ARAYUZ_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>ARAŞTIRMACI KONTROL PANELİ (OTOPİLOT)</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; padding: 40px; text-align: center; }
        .container { max-width: 600px; background: white; padding: 30px; border-radius: 8px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 80%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #1a365d; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2b6cb0; }
        #sonuc { margin-top: 20px; text-align: left; background: #e2e8f0; padding: 15px; border-radius: 4px; display: none; white-space: pre-wrap; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔍 OTOPİLOT ARAŞTIRMA PANELİ</h2>
        <p>YouTube Video ID'sini girin, sistem en güncel modeli kendi seçip analiz etsin.</p>
        <input type="text" id="videoId" placeholder="Örn: dQw4w9WgXcQ">
        <br>
        <button onclick="arastirmayaBasla()">ARAŞTIR VE ANALİZ ET</button>
        <div id="sonuc"></div>
    </div>

    <script>
        async function arastirmayaBasla() {
            const vId = document.getElementById('videoId').value.trim();
            const btn = document.querySelector('button');
            const sonucDiv = document.getElementById('sonuc');
            if(!vId) { alert('Lütfen bir Video ID girin!'); return; }
            
            btn.innerText = "Otopilot Model Seçiyor ve Analiz Ediyor... Bekleyin...";
            btn.disabled = true;
            sonucDiv.style.display = "none";
            sonucDiv.innerHTML = "";

            try {
                let formData = new FormData();
                formData.append('video_id', vId);
                
                let response = await fetch('/arastir', { method: 'POST', body: formData });
                let data = await response.json();
                
                sonucDiv.style.display = "block";
                if(data.durum === "basarili") {
                    sonucDiv.innerHTML = "<b>✅ BAŞARILI! Veri Bulut Kasasına Kaydoldu.</b><br><br><b>🤖 Otopilotun Seçtiği Model:</b> <code>" + data.kullanilan_model + "</code><br><br><b>🧠 Yapay Zeka Raporu:</b><br>" + data.analiz;
                } else {
                    sonucDiv.innerHTML = "<b>❌ Hata Oluştu:</b><br>" + data.mesaj;
                }
            } catch(e) {
                sonucDiv.style.display = "block";
                sonucDiv.innerHTML = "<b>❌ Sistem bir hata verdi:</b><br>" + e;
            }
            btn.innerText = "ARAŞTIR VE ANALİZ ET";
            btn.disabled = false;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def ana_sayfa():
    return ARAYUZ_HTML

# --- 5. TAM OTONOM İŞLEM DÜĞÜMÜ: METNE DÖNÜŞTÜR -> MODELİ KENDİ SEÇ -> ANALİZ ET -> KAYDET ---
@app.post("/arastir")
async def video_arastir(video_id: str = Form(...)):
    if not supabase:
        return JSONResponse(content={"durum": "hata", "mesaj": "Veritabanı bağlantısı kurulamadı. Şifreleri kontrol edin."})
        
    try:
        # İŞLEM 1: Videoyu baştan sona eksiksiz metne dönüştür
        loop = asyncio.get_event_loop()
        transcript_list = await loop.run_in_executor(
            None, lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en'])
        )
        tam_metin = " ".join([t['text'] for t in transcript_list])
        
        # İŞLEM 2: Otopilotu devreye sok ve o anki EN GÜNCEL modeli kendi kendine seçtir!
        secilen_model_adi = await loop.run_in_executor(None, en_guncel_modeli_sec)
        
        # İŞLEM 3: Seçilen otonom model ile derinlemesine analiz yap
        model = genai.GenerativeModel(secilen_model_adi)
        prompt = f"Aşağıdaki konuşma metnini eksiksiz, insan gibi derinlemesine incele ve bana en can alıcı noktalarını kronolojik özet halinde Türkçe raporla:\n\n{tam_metin}"
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        yapay_zeka_raporu = response.text
        
        # İŞLEM 4: Elde edilen tüm veriyi, analizi ve kullanılan modeli Supabase'e kalıcı olarak kaydet
        veri_blogu = {
            "video_id": video_id,
            "baslik": f"Video {video_id}",
            "konusma_metni": tam_metin,
            "kullanilan_model": secilen_model_adi,
            "yapay_zeka_analizi": {"rapor": yapay_zeka_raporu}
        }
        await loop.run_in_executor(None, lambda: supabase.table("arastirmaci_verileri").insert(veri_blogu).execute())
        
        return JSONResponse(content={"durum": "basarili", "kullanilan_model": secilen_model_adi, "analiz": yapay_zeka_raporu})
    except Exception as e:
        return JSONResponse(content={"durum": "hata", "mesaj": str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
