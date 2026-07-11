import os
import asyncio
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from supabase import create_client, Client
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# Bulut Sunucusundaki Gizli Şifreleri Güvenli Odadan Çağırıyoruz
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Sistem Bağlantılarını Başlatıyoruz
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

app = FastAPI()

# Şık ve Sade Bir Kullanıcı Arayüzü (HTML)
ARAYUZ_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ARAŞTIRMACI KONTROL PANELİ</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; padding: 40px; text-align: center; }
        .container { max-width: 600px; background: white; padding: 30px; border-radius: 8px; margin: 0 auto; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        input[type="text"] { width: 80%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #1a365d; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background: #2b6cb0; }
        #sonuc { margin-top: 20px; text-align: left; background: #e2e8f0; padding: 15px; border-radius: 4px; display: none; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔍 ARAŞTIRMACI SİSTEMİ PANELİ</h2>
        <p>YouTube Video ID'sini girin, bulut sistemimiz saniyeler içinde analiz etsin.</p>
        <input type="text" id="videoId" placeholder="Örn: dQw4w9WgXcQ (Videonun linkindeki v= kısmından sonraki kod)">
        <br>
        <button onclick="arastirmayaBasla()">ARAŞTIR VE ANALİZ ET</button>
        <div id="sonuc"></div>
    </div>

    <script>
        async function arastirmayaBasla() {
            const vId = document.getElementById('videoId').value;
            const btn = document.querySelector('button');
            const sonucDiv = document.getElementById('sonuc');
            if(!vId) { alert('Lütfen bir Video ID girin!'); return; }
            
            btn.innerText = "Bulut Ordusu Çalışıyor... Lütfen Bekleyin...";
            btn.disabled = true;
            sonucDiv.style.display = "none";

            try {
                let formData = new FormData();
                formData.append('video_id', vId);
                
                let response = await fetch('/arastir', { method: 'POST', body: formData });
                let data = await response.json();
                
                sonucDiv.style.display = "block";
                if(data.durum === "basarili") {
                    sonucDiv.innerHTML = "<b>BAŞARILI! Veri Bulut Kasasına Kaydoldu.</b>\\n\\n<b>Yapay Zeka Raporu:</b>\\n" + data.analiz;
                } else {
                    sonucDiv.innerHTML = "<b>Hata Oluştu:</b>\\n" + data.mesaj;
                }
            } catch(e) {
                alert('Sistem bir hata verdi!');
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

@app.post("/arastir")
async def video_arastir(video_id: str = Form(...)):
    try:
        # 1. Adım: Videonun altyazı metnini YouTube sunucularından saniyeler içinde havada yakalıyoruz
        loop = asyncio.get_event_loop()
        transcript_list = await loop.run_in_executor(
            None, lambda: YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en'])
        )
        tam_metin = " ".join([t['text'] for t in transcript_list])
        
        # 2. Adım: Milyonlarca kelime olsa dahi bir kerede yutabilen Gemini API'ye metni analize gönderiyoruz
        prompt = f"Aşağıdaki konuşma metnini eksiksiz, insan gibi derinlemesine incele ve bana en can alıcı noktalarını kronolojik özet halinde Türkçe raporla:\n\n{tam_metin}"
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        yapay_zeka_raporu = response.text
        
        # 3. Adım: Bilgisayarına hiç indirmeden veriyi doğrudan Frankfurt'taki bulut kasasına yazıyoruz
        veri_blogu = {
            "video_id": video_id,
            "baslik": f"Video {video_id}",
            "konusma_metni": tam_metin,
            "yapay_zeka_analizi": {"rapor": yapay_zeka_raporu}
        }
        await loop.run_in_executor(None, lambda: supabase.table("arastirmaci_verileri").insert(veri_blogu).execute())
        
        return JSONResponse(content={"durum": "basarili", "analiz": yapay_zeka_raporu})
    except Exception as e:
        return JSONResponse(content={"durum": "hata", "mesaj": str(e)})
