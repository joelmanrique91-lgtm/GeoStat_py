cd "C:\Users\joelm\Documents\aster_app\aster-mineral-mapper"

while ($true) {
    Write-Host "======================================"
    Write-Host "Actualizando desde GitHub..."
    Write-Host "======================================"

    git fetch origin
    git status -sb

    git pull --ff-only origin main

    python -m pip install -r requirements.txt

    Write-Host "======================================"
    Write-Host "Levantando Streamlit en localhost:8501"
    Write-Host "======================================"

    python -m streamlit run app.py --server.port 8501

    Write-Host "Streamlit se cerró. Reintentando actualización en 5 segundos..."
    Start-Sleep -Seconds 5
}
