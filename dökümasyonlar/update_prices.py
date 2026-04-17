import csv
import urllib.request
import json
from decimal import Decimal

def get_usd_try_rate():
    try:
        with urllib.request.urlopen('https://api.exchangerate-api.com/v4/latest/USD') as response:
            data = json.loads(response.read().decode())
            return Decimal(str(data['rates']['TRY']))
    except:
        try:
            with urllib.request.urlopen('https://open.er-api.com/v6/latest/USD') as response:
                data = json.loads(response.read().decode())
                return Decimal(str(data['rates']['TRY']))
        except:
            print("Dolar kuru çekilemedi, varsayılan kur kullanılıyor: 34.50")
            return Decimal('34.50')

def update_csv_with_tl_prices():
    usd_try_rate = get_usd_try_rate()
    print(f"Anlık USD/TRY kuru: {usd_try_rate}")
    
    input_file = 'EMİR YILMAZ ÇALIŞMA.csv'
    output_lines = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line = line.rstrip('\n')
        parts = line.split(';')
        
        if i == 0 or i == 4:
            if len(parts) == 14:
                parts.append('BİRİM FİYAT TL')
                parts.append('TOPLAM MALİYET TL')
            elif len(parts) == 15:
                parts.append('TOPLAM MALİYET TL')
        else:
            if len(parts) == 14:
                unit_price_usd = parts[13].replace(' USD', '').replace('.', '').replace(',', '.')
                unit_price_decimal = Decimal(unit_price_usd)
                unit_price_tl = unit_price_decimal * usd_try_rate
                parts.append(f'{unit_price_tl:.2f} TL'.replace('.', ','))
                
                total_cost_usd = parts[12].replace(' USD', '').replace('.', '').replace(',', '.')
                total_cost_decimal = Decimal(total_cost_usd)
                total_cost_tl = total_cost_decimal * usd_try_rate
                parts.append(f'{total_cost_tl:.2f} TL'.replace('.', ','))
            elif len(parts) == 15:
                total_cost_usd = parts[12].replace(' USD', '').replace('.', '').replace(',', '.')
                total_cost_decimal = Decimal(total_cost_usd)
                total_cost_tl = total_cost_decimal * usd_try_rate
                parts.append(f'{total_cost_tl:.2f} TL'.replace('.', ','))
        
        output_lines.append(';'.join(parts))
    
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print("CSV dosyası başarıyla güncellendi!")

if __name__ == '__main__':
    update_csv_with_tl_prices()
