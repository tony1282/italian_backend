#!/usr/bin/env python
# Script para limpiar espacios en devoluciones/services.py

import re

with open('devoluciones/services.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar y reemplazar el patrón de espacios innecesarios
old_pattern = r'''MovimientoInventario\.objects\.create\(\s+variante=variante,\s+tipo="DEVOLUCION",\s+stock_anterior=stock_anterior,\s+cantidad=detalle\.cantidad,\s+stock_nuevo=stock_nuevo,\s+stock_defectuoso_anterior=\(\s+stock_defectuoso_anterior\s+\),\s+stock_defectuoso_nuevo=\(\s+stock_defectuoso_nuevo\s+\),\s+observaciones=\(\s+f"Devoluci[óo]n \{devolucion\.id\}"\s+\),\s+usuario=usuario\s+\)'''

new_pattern = '''MovimientoInventario.objects.create(
            variante=variante,
            tipo="DEVOLUCION",
            stock_anterior=stock_anterior,
            cantidad=detalle.cantidad,
            stock_nuevo=stock_nuevo,
            stock_defectuoso_anterior=stock_defectuoso_anterior,
            stock_defectuoso_nuevo=stock_defectuoso_nuevo,
            observaciones=f"Devolución {devolucion.id}",
            usuario=usuario
        )'''

# Más simple: encontrar el patrón específico
lines = content.split('\n')
result = []
i = 0
while i < len(lines):
    if 'MovimientoInventario.objects.create(' in lines[i] and i > 730 and i < 760:
        # Esto es el patrón que queremos cambiar
        # Saltamos hasta el final del create
        result.append('        MovimientoInventario.objects.create(')
        result.append('            variante=variante,')
        result.append('            tipo="DEVOLUCION",')
        result.append('            stock_anterior=stock_anterior,')
        result.append('            cantidad=detalle.cantidad,')
        result.append('            stock_nuevo=stock_nuevo,')
        result.append('            stock_defectuoso_anterior=stock_defectuoso_anterior,')
        result.append('            stock_defectuoso_nuevo=stock_defectuoso_nuevo,')
        result.append('            observaciones=f"Devolución {devolucion.id}",')
        result.append('            usuario=usuario')
        result.append('        )')
        # Saltar las líneas del patrón antiguo
        while i < len(lines) and ')' not in lines[i]:
            i += 1
        if i < len(lines) and ')' in lines[i]:
            i += 1
    else:
        result.append(lines[i])
        i += 1

with open('devoluciones/services.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(result))

print("Archivo actualizado")
