# 🎨 Charte Graphique UI – Universel & Multiplateforme

Cette charte graphique est conçue pour assurer **cohérence, accessibilité et portabilité** à travers toutes les plateformes et frameworks (Web, Mobile, Desktop). Elle définit les couleurs, typographies, composants UI et leurs états, dans un format générique adaptable.

---

## 🌈 Palette de Couleurs

### 🎨 Palette Principale

| Nom         | Hex      | Rôle |
|-------------|----------|------|
| Bleu pétrole | `#264C6E` | Couleur d'ancrage, profondeur, confiance |
| Corail doux  | `#F27B70` | Accent principal, émotion, chaleur |
| Vert sauge   | `#A3C9A8` | Couleur secondaire, calme et nature |
| Jaune pastel | `#FFD882` | Accent léger, lumière, joie |
| Beige ivoire | `#FDF8EF` | Fond neutre, papier, douceur |

### 🌞🌚 Modes Jour & Nuit

| Élément UI              | Light Mode | Dark Mode | Description |
|------------------------|------------|-----------|-------------|
| Primary                | `#F27B70`  | `#F58C82` | Accent principal |
| Secondary              | `#A3C9A8`  | `#ADCBB3` | Accent secondaire |
| Tertiary               | `#FFD882`  | `#FFEBA6` | Accent léger / badges |
| Background             | `#FDF8EF`  | `#1F1F1F` | Fond principal |
| Surface                | `#FFFFFF`  | `#2A2A2A` | Fond composants |
| On Primary             | `#FFFFFF`  | `#1F1F1F` | Texte sur primary |
| On Background          | `#3A3A3A`  | `#F1F1F1` | Texte principal |
| On Surface             | `#444444`  | `#E0E0E0` | Texte secondaire |
| Border / Divider       | `#DADADA`  | `#555555` | Séparateurs |
| Error                  | `#D9605E`  | `#F58C8A` | Alerte critique |
| Success                | `#77C29B`  | `#93D1B1` | Validation |
| Disabled               | `#C5C5C5`  | `#707070` | Inactif |
| Focus / Outline        | `#6F9FD2`  | `#99BFF2` | Focus visible |

---

## 🔠 Typographie

| Usage     | Police principale     | Alternatives       | Poids recommandés |
|-----------|-----------------------|--------------------|-------------------|
| Titres    | Nunito Sans, Baloo 2  | Poppins, Raleway   | 600–800           |
| Texte     | Figtree, DM Sans      | Inter, Open Sans   | 400–600           |
| Technique | JetBrains Mono        | Rubik Mono One     | 400–500           |

- **Taille minimum** : 14px
- **Taille conseillée corps texte** : 16px
- **Contraste** : Respect WCAG AA/AAA

---

## 🧩 Design Tokens (abstraits)

```yaml
color:
  primary: "#F27B70"
  onPrimary: "#FFFFFF"
  secondary: "#A3C9A8"
  surface: "#FFFFFF"
  background: "#FDF8EF"
  onSurface: "#444444"
  error: "#D9605E"
  success: "#77C29B"
  focus: "#6F9FD2"
  disabled: "#C5C5C5"
```

---

## 📦 Composants UI

### 🧭 Navigation

- AppBar : `background`, texte `onBackground`, ombre en scroll
- Bottom Navigation : `primary` (sélectionné), `onSurface` (inactif)
- Drawer : fond `surface`, texte actif `secondary`
- TabBar : onglet actif `primary`, inactif `onSurface`

### 💬 Boutons

| Type             | Fond       | Texte        | Hover / Focus / Disabled |
|------------------|------------|--------------|---------------------------|
| ElevatedButton   | Primary    | OnPrimary    | Ombre, couleur foncée     |
| OutlinedButton   | Surface    | Primary      | Bordure `focus`           |
| TextButton       | Transparent| Primary      | Texte souligné ou gras    |
| IconButton       | Primary    | OnPrimary    | Cercle focus + ombre      |
| FAB              | Primary    | OnPrimary    | Ombre + changement couleur|

### 🧾 Champs de saisie

- Fond : `surface`
- Bordure : `border`
- Texte : `onSurface`
- Placeholder : `disabled`
- Texte d’erreur : `error`
- État focus : `focus` (bordure ou ombre)

### 📚 Listes & Cartes

- Card : `surface`, texte `onSurface`, légère ombre
- Chip : `secondary` ou `tertiary`, texte `onSecondary`
- ListTile : survol `focus`, sélection `primary`

### 📢 États & Alertes

| Type       | Couleur      | Texte / Icône |
|------------|--------------|----------------|
| Info       | Tertiary     | OnBackground   |
| Succès     | Success      | OnSurface      |
| Alerte     | Error        | OnPrimary      |
| Désactivé  | Disabled     | OnSurface 50%  |
| Focus      | Focus        | Contour/ombre  |

---

## ⚙️ États UI communs

- **Hover** : légère ombre ou teinte plus foncée
- **Focus** : contour coloré ou halo
- **Active** : couleur plus saturée
- **Disabled** : opacité 40–60% ou couleur dédiée
- **Selected** : fond `primary` ou `secondary` plus clair

---

## 🌐 Accessibilité

- Tous les contrastes sont conformes **WCAG 2.1** niveau **AA** minimum, AAA pour les éléments critiques.
- Focus visible toujours présent (outline, ombre).
- Navigation clavier compatible pour tous les composants interactifs.
- Aucune animation ne doit bloquer la compréhension ni durer plus de 5 secondes sans contrôle utilisateur.

---

## 🧩 Branding produit – (exemple TalesTide)

- Carte RFID scannée : fond `tertiary`, halo `focus`
- Onde sonore : dégradé `primary` → `secondary`
- Badge open source : `success` + bordure `primary`
- Encart narration : fond `tertiary`, texte `onTertiary`

---

## 📱 Intégration multiplateforme

- **Web / CSS** : via `:root { --color-primary: #F27B70; }`
- **Flutter** : `ThemeData` et `ColorScheme` Material 3
- **iOS** : UIColor avec Asset Catalogs
- **Android** : XML `colors.xml`
- **React / Tailwind** : via `theme.extend.colors`

---

## 📂 Structure recommandée

```
/tokens/
  colors.yaml
  typography.yaml
/themes/
  theme.light.json
  theme.dark.json
flutter/
  lib/theme/colors.dart
web/
  styles/theme.css
```
