#!/bin/bash

echo "Monitoring for completion of full dataset tagging..."
echo "Started monitoring at: $(date)"

while true; do
    if [ -f "data/processed/test_osd_enriched_tagged_fixed.csv" ]; then
        echo "✅ Full dataset tagging complete at $(date)!"
        echo "Switching Streamlit to full dataset..."
        
        # Kill current Streamlit
        pkill -f "streamlit run"
        sleep 2
        
        # Launch with full dataset
        nohup streamlit run app/streamlit_app.py -- --input "data/processed/test_osd_enriched_tagged_fixed.csv" --weights "High=1.0,Medium=0.5,Low=0.1" > streamlit_full.log 2>&1 &
        
        echo "🚀 New Streamlit launched with full dataset!"
        echo "Check http://localhost:8501"
        break
    fi
    
    echo "Still processing... $(date)"
    sleep 30  # Check every 30 seconds
done
