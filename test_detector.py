#!/usr/bin/env python3
import sys
sys.path.insert(0, './src')
sys.path.insert(0, './src/detector')

from detector import AliyahSaleDetector

print('🧪 בדיקת Detector משופר')
print('=' * 60)

detector = AliyahSaleDetector()

tests = [
    'נמכרה עלייה שלישית למר משה כהן בעד שלוש מאות שקל',
    'קונה דוד לוי עלייה רביעית תמורת 250 שקלים',
    'מפטיר נמכר לרבי יוסף בן אברהם במחיר של חמש מאות שקל',
]

for i, text in enumerate(tests, 1):
    print(f'\n[{i}] {text}')
    sales = detector.detect_aliyah_sales({'text': text})
    if sales:
        for sale in sales:
            name = sale.get("buyer_name", "?")
            typ = sale.get("aliyah_type", "?")
            amt = sale.get("amount", "?")
            conf = sale.get("confidence", 0)
            print(f'   ✓ {name} | {typ} | {amt}₪ | {conf:.0f}%')
    else:
        print('   ✗ לא זוהתה מכירה')

print('\n' + '=' * 60)
