# Detect who is talking on Discord

🇬🇧 English · 🇪🇸 [Español](discord.es.md) · [← Back to the README](../README.md)

For **“Lower music when talking”** to work properly (without being fooled by music or notification sounds), the Mixer needs to know who is talking in your voice channel. Discord allows that through a **free** developer application and a permission you accept once. You need the **Discord desktop app** open on the PC.

## Steps

1. **Create an application on Discord.** Go to <https://discord.com/developers/applications> with your account, click *New Application*, name it “Mixer” and accept.

2. **Add the redirect address.** In the left menu, **OAuth2**. Under *Redirects* click *Add Redirect* and type exactly `http://localhost`. Click *Save Changes*.

3. **Copy the two codes.**
   - **Application ID:** in *General Information* (a long number).
   - **Client Secret:** in *OAuth2* → *Client Secret* → *Reset Secret*, then copy the text. It is shown only once; if you lose it, reset it again. **It is like a password: don't share it.**

4. **Give them to the Mixer.** Double-click `setup-discord.bat`. Paste the Application ID (Enter) and the Client Secret (Enter).

5. **Accept the permission.** In a few seconds Discord will show a window: “Mixer wants to access your account”. Click **Authorize**. It is only asked the first time.

Done: under “Lower music when talking”, the Mixer will show your voice channel's name and who is talking.

## If something fails

The reason is written in that same area of the Mixer screen. You can also check `rpc.log`.

## Remove everything

Delete the `discord_rpc.json` file and, in the portal, the “Mixer” application.

> Discord's local connection (RPC) is a restricted Discord feature: it works with an application of your own and your own account, but Discord may change it.
