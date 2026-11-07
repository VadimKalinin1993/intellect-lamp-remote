<p align="center"><img src="icon.png" width="96" alt="Lamp app icon"></p>

<h1 align="center">Lamp: a calm remote for the Intellect WLED lamp</h1>

<p align="center">A simple, good-looking replacement for the stock WLED interface.<br>It's one file that lives inside the lamp itself and works on any phone or computer on your Wi‑Fi.</p>

![Lamp app: colors, scenes and sleep timer](screenshots/preview.png)

## What it does

- **On/off**: tap the big orb. It shows the lamp's live colors in real time.
- **Brightness**: one large slider; tap or drag anywhere on it.
- **Colors**: 12 ready-made colors (warm whites plus soft tones), and a color wheel under **Custom** for saving your own.
- **Scenes**: 10 calm, pre-tuned animations made for a diffused lamp: Candle, Embers, Breathe, Ocean, Aurora, Sunset, Lagoon, Fireflies, Pastel and Spectrum. Each scene has its own speed and intensity sliders. The full list of WLED effects is still there under **All WLED effects**.
- **Sleep timer**: the lamp fades out over 3, 5, 15, 30 or 60 minutes, with a countdown at the top.
- **Recent**: one tap takes you back to the color or scene you had before.
- **Home Screen app**: has its own icon and opens full screen, like a native app.

Nothing is sent to the internet. The app talks only to your lamp, over your home network.

## What you need

- An **Intellect** lamp (or any lamp running **WLED**; the app was built and tested on WLED 0.14 with an ESP8266 and 87 LEDs).
- The lamp already set up and connected to your Wi‑Fi.
- A phone or computer on **the same Wi‑Fi network**.

## Install (about 2 minutes)

### 1. Download the files

On this page, click the green **Code** button → **Download ZIP**, then unzip it.
You only need two files from it: **`app.htm`** and **`icon.png`**.

### 2. Find your lamp's address

The lamp's address looks like `192.168.1.133`. You can find it:

- in the official **WLED** app: open the lamp, and the address is shown in the lamp's info or settings;
- or in your Wi‑Fi router's list of connected devices (it usually shows up as `WLED` or `INTELLECT`).

In the steps below, replace `LAMP-ADDRESS` with that address.

### 3. (Recommended) Back up the lamp's settings

Open `http://LAMP-ADDRESS/` in a browser → **Config** → **Security & Updates**, then click **Backup presets** and **Backup configuration**. You'll get two small files you can restore later from the same page.

### 4. Upload the app to the lamp

1. Open **`http://LAMP-ADDRESS/edit`** in a browser on your computer.
2. At the top, click **Choose file**, select **`app.htm`**, then click **Upload**.
3. Do the same for **`icon.png`**.

Both files now appear in the list on the left.

### 5. Open it

Open **`http://LAMP-ADDRESS/app.htm`**. You should see the orb and a green **Connected** pill at the top.

### 6. Add it to your Home Screen

- **iPhone (Safari):** tap **Share** → **Add to Home Screen** → **Add**.
- **Android (Chrome):** tap **⋮** → **Add to Home screen**.

Now it opens like a regular app, with its own icon.

## Using it with several people

Anyone on the same Wi‑Fi can open `http://LAMP-ADDRESS/app.htm` on their own phone and add it to their Home Screen. You all control the same lamp and see the same state: on/off, brightness, color, scene and timer.

Saved custom colors and the **Recent** pill are kept per device, in that phone's browser.

## Updating

Download the new `app.htm` and upload it through `http://LAMP-ADDRESS/edit` again. It replaces the old one. If the icon changed too, upload the new `icon.png`, then remove the Home Screen shortcut and add it again (phones cache the icon).

## Removing

Open `http://LAMP-ADDRESS/edit`, right-click `app.htm` (and `icon.png`) in the file list, and choose **Delete**. The lamp is back to exactly how it was. The stock WLED interface at `http://LAMP-ADDRESS/` is never changed, so you can use it at any time.

## Troubleshooting

**The pill at the top says "Offline".** Check that the lamp is plugged in and that your phone is on the same Wi‑Fi network (not mobile data or a guest network).

**It worked yesterday, but today the page doesn't open.** Your router probably gave the lamp a new address. Find the new one (step 2) and add the shortcut again. To stop this from happening, reserve the lamp's address in your router settings (often called *DHCP reservation* or *static lease*).

**The app doesn't work outside home.** That's expected: it only works on your home network. WLED has no password protection for control, so don't expose the lamp to the internet. If you need remote access, use a VPN such as Tailscale.

**A scene looks different from what I expected.** LEDs behind a diffuser mix colors a bit differently from a screen. Use the scene's speed and intensity sliders to adjust it.

## Files

| File | What it is |
|---|---|
| `app.htm` | The whole app: one self-contained page. |
| `icon.png` | The Home Screen icon. |
| `screenshots/` | Images for this page; you don't need to upload them. |
