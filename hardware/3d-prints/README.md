# Pièces imprimées en 3D — TheOpenMusicBox (RPi)

La structure du boîtier est imprimée en 3D, en PLA. Ces pièces forment l'ossature du cube, dans laquelle viennent s'insérer les panneaux MDF découpés au laser (voir [`../laser-cut/`](../laser-cut/)).

## Versions

La fabrication actuelle combine deux générations :
- **V2.2** : version la plus complète, sert de référence pour le corps et les côtés.
- **V2.3** : itération suivante avec dos et fond revus pour intégrer les boutons sur le dessus et faciliter l'accès à la batterie.

À fabriquer : prendre **tout V2.2 sauf `Back_*` et `Bottom_*` qui sont remplacés par leurs équivalents V2.3**.

## Liste des pièces

| Fichier | Rôle | Notes |
|---------|------|-------|
| `Body_TMB_V2.2.stl` | Corps principal, ossature cubique | Pièce la plus longue à imprimer (~10 h) |
| `Front_TMB_V2.2.stl` | Face avant | Plus lisse en V2.3 (boutons retirés de la façade) |
| `Top_TMB_V2.2.stl` | Dessus du boîtier | À adapter si vous voulez les boutons sur le dessus |
| `Back_TMB_V2.3.stl` | Dos avec trappe batterie | Remplace `Back_TMB_V2.2.stl` |
| `Bottom_TMB_V2.3.stl` | Fond | Remplace `Bottom_TMB_V2.2.stl` |
| `Bottom-top_TMB_V2.2.stl` | Plateau interne | Sert de support aux composants |
| `bottom-door_TMB_V2.2.stl` | Petite porte du fond | Accès rapide sans démontage |
| `left_side_V2.2.stl` / `right_side_V2.2.stl` | Côtés | Identiques en miroir |

Fichiers V2.2 conservés à titre de référence (`Back_TMB_V2.2.stl`, `Bottom_TMB_V2.2.stl`) au cas où vous voulez la version antérieure.

## Paramètres d'impression recommandés

- **Imprimante testée** : Prusa MK4 / MK4S
- **Matériau** : PLA (rouge, mais n'importe quelle couleur fait l'affaire)
- **Hauteur de couche** : 0.2 mm (équilibre temps / finition)
- **Buse** : 0.4 mm
- **Densité de remplissage** : 15 % grid
- **Supports** : nécessaires sur `Body` et `Front` selon orientation
- **Bord (brim)** : 5 mm conseillé pour le corps (longues pièces)

Temps d'impression cumulé environ **18 à 22 heures** pour l'ensemble.

## Assemblage

L'ordre conseillé :
1. Imprimer toutes les pièces.
2. Insérer les inserts à chaud M3 dans les emplacements prévus.
3. Préparer les panneaux MDF (voir `../laser-cut/`).
4. Pré-assembler les composants électroniques sur le `Bottom-top` (plateau interne).
5. Visser les côtés sur le corps, glisser le plateau, refermer dessus / fond.

Documentation pas-à-pas illustrée en cours. Pour l'instant, le [STEP complet est disponible](../) si besoin de visualiser l'assemblage avant impression.
