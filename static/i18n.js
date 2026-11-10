/* Idiomas de la interfaz (es / en) · UI languages (es / en)
 *
 * Idioma: ?lang=es|en en la dirección > el elegido con el botón ES·EN (se recuerda) > el del navegador.
 * Language: ?lang=es|en in the URL > the one picked with the ES·EN button (remembered) > the browser's.
 *
 * t('clave', {variable: valor})   -> texto traducido · translated text
 * data-i18n / data-i18n-aria      -> en el HTML, se rellenan solos · filled automatically in the HTML
 */
(function () {
  const D = {
    es: {
      'conn.connecting': 'Conectando…', 'conn.online': 'En línea', 'conn.reconnecting': 'Reconectando…', 'conn.error': 'Error: {msg}',

      'act.muteAll': 'Silenciar todo', 'act.restore': 'Restaurar sonido', 'act.edit': 'Editar canales', 'act.done': 'Listo',

      'duck.btn': 'Bajar música al hablar', 'duck.active': 'Música bajada',
      'duck.downTo': 'Baja hasta', 'duck.downToAria': 'Nivel al que baja la música',
      'duck.triggerAt': 'Se activa con', 'duck.triggerAria': 'Nivel de sonido a partir del cual se baja la música',
      'duck.threshold': 'Raya en {n}%', 'duck.measure': 'Medir silencio', 'duck.measuring': 'Midiendo… no hables',
      'duck.voiceHint': 'Cuando nadie hable, la barra verde no debe pasar de la raya. Si la pasa, pulsa «Medir silencio» con nadie hablando durante 4 segundos.',
      'duck.editHint': '«Voz» hace que, cuando suene esa app, bajen los canales marcados con «Bajar». Solo actúa si «Bajar música al hablar» está activado.',

      'rpc.talk1': 'alguien habla', 'rpc.talkN': '{n} personas hablan', 'rpc.quiet': 'nadie habla',
      'rpc.noChannel': 'Conectado a Discord. Entra en un canal de voz para detectar quién habla.',
      'rpc.fallback': '{status} · mientras tanto se usa el volumen, que falla si Discord reproduce música.',
      'rpc.setup': 'Detección por volumen, poco fiable si Discord reproduce música. Para detectar la voz de verdad, ejecuta setup-discord.bat en el PC (instrucciones en docs/discord.es.md).',
      'rpc.st.unconfigured': 'Sin configurar: ejecuta setup-discord.bat', 'rpc.st.connecting': 'Conectando con Discord…',
      'rpc.st.authorize': 'Acepta el permiso en la ventana de Discord…', 'rpc.st.connected': 'Conectado a Discord',
      'rpc.st.error': 'Sin conexión con Discord: {detail}',

      'empty.default': 'No suena nada ahora mismo. Cuando abras una app con sonido, aparecerá como un canal nuevo.',
      'empty.hidden': 'Todas las apps con sonido están ocultas. Pulsa «Editar canales» para volver a mostrarlas.',
      'empty.noOutput': 'No hay ninguna salida de audio activa. Enciende los auriculares o conecta unos altavoces y volverá solo.',

      'ch.master': 'General', 'ch.mic': 'Micro', 'ch.mute': 'Mute', 'ch.muteAria': 'Silenciar {name}',
      'ch.pin': 'Fijar', 'ch.pinned': 'Fijado', 'ch.hide': 'Ocultar', 'ch.hidden': 'Oculto', 'ch.voice': 'Voz', 'ch.lower': 'Bajar',
      'ch.pinAria': 'Fijar {name} arriba', 'ch.hideAria': 'Ocultar {name}', 'ch.voiceAria': '{name} es una app de voz',
      'ch.lowerAria': 'Bajar {name} cuando hable la voz', 'ch.goto': 'Ir al canal {name}',

      'dev.headphones': 'Auriculares', 'dev.speakers': 'Altavoces', 'dev.monitor': 'Monitor', 'dev.outputAria': 'Salida de audio',
      'media.untitled': 'Sin título', 'media.prev': 'Anterior', 'media.play': 'Reproducir o pausar', 'media.next': 'Siguiente',

      'login.hint': 'Solo te lo pedirá esta vez en este dispositivo.', 'login.prompt': 'Introduce el PIN', 'login.enter': 'Entrar',
      'login.entering': 'Entrando…', 'login.bad': 'PIN incorrecto. Te quedan {n} intentos.', 'login.wrong': 'PIN incorrecto',
      'login.locked': 'Demasiados intentos. Prueba de nuevo en {t}', 'login.noConn': 'No hay conexión con el PC.',
      'login.fail': 'No se pudo comprobar el PIN', 'login.delete': 'Borrar',
      'login.broken': 'El archivo del PIN está dañado: vuelve a ejecutar setup-pin.bat',
    },
    en: {
      'conn.connecting': 'Connecting…', 'conn.online': 'Online', 'conn.reconnecting': 'Reconnecting…', 'conn.error': 'Error: {msg}',

      'act.muteAll': 'Mute all', 'act.restore': 'Restore sound', 'act.edit': 'Edit channels', 'act.done': 'Done',

      'duck.btn': 'Lower music when talking', 'duck.active': 'Music lowered',
      'duck.downTo': 'Lower to', 'duck.downToAria': 'Level the music is lowered to',
      'duck.triggerAt': 'Triggers at', 'duck.triggerAria': 'Sound level above which the music is lowered',
      'duck.threshold': 'Line at {n}%', 'duck.measure': 'Measure silence', 'duck.measuring': 'Measuring… stay quiet',
      'duck.voiceHint': 'When nobody is talking, the green bar should stay below the line. If it doesn’t, press “Measure silence” while nobody talks for 4 seconds.',
      'duck.editHint': '“Voice” means that when that app makes sound, the channels marked “Lower” are turned down. It only works if “Lower music when talking” is on.',

      'rpc.talk1': 'someone is talking', 'rpc.talkN': '{n} people are talking', 'rpc.quiet': 'nobody is talking',
      'rpc.noChannel': 'Connected to Discord. Join a voice channel to detect who is talking.',
      'rpc.fallback': '{status} · using the volume level meanwhile, which fails if Discord plays music.',
      'rpc.setup': 'Volume-based detection, unreliable if Discord plays music. For real voice detection, run setup-discord.bat on the PC (see docs/discord.en.md).',
      'rpc.st.unconfigured': 'Not set up: run setup-discord.bat', 'rpc.st.connecting': 'Connecting to Discord…',
      'rpc.st.authorize': 'Accept the permission in the Discord window…', 'rpc.st.connected': 'Connected to Discord',
      'rpc.st.error': 'Can’t reach Discord: {detail}',

      'empty.default': 'Nothing is playing right now. When you open an app that makes sound, it will show up as a new channel.',
      'empty.hidden': 'All apps with sound are hidden. Press “Edit channels” to show them again.',
      'empty.noOutput': 'There is no active audio output. Turn on your headphones or plug in speakers and it will come back by itself.',

      'ch.master': 'Master', 'ch.mic': 'Mic', 'ch.mute': 'Mute', 'ch.muteAria': 'Mute {name}',
      'ch.pin': 'Pin', 'ch.pinned': 'Pinned', 'ch.hide': 'Hide', 'ch.hidden': 'Hidden', 'ch.voice': 'Voice', 'ch.lower': 'Lower',
      'ch.pinAria': 'Pin {name} to the top', 'ch.hideAria': 'Hide {name}', 'ch.voiceAria': '{name} is a voice app',
      'ch.lowerAria': 'Lower {name} when the voice app is active', 'ch.goto': 'Go to channel {name}',

      'dev.headphones': 'Headphones', 'dev.speakers': 'Speakers', 'dev.monitor': 'Monitor', 'dev.outputAria': 'Audio output',
      'media.untitled': 'Untitled', 'media.prev': 'Previous', 'media.play': 'Play or pause', 'media.next': 'Next',

      'login.hint': 'It will only ask for this once on this device.', 'login.prompt': 'Enter PIN', 'login.enter': 'Enter',
      'login.entering': 'Signing in…', 'login.bad': 'Wrong PIN. {n} attempts left.', 'login.wrong': 'Wrong PIN',
      'login.locked': 'Too many attempts. Try again in {t}', 'login.noConn': 'Can’t reach the PC.',
      'login.fail': 'Couldn’t check the PIN', 'login.delete': 'Delete',
      'login.broken': 'The PIN file is damaged: run setup-pin.bat again',
    },
  };

  const KEY = 'mixer_lang';
  function pick() {
    const q = new URLSearchParams(location.search).get('lang');
    if (q === 'es' || q === 'en') { try { localStorage.setItem(KEY, q); } catch (e) {} return q; }
    try { const s = localStorage.getItem(KEY); if (s === 'es' || s === 'en') return s; } catch (e) {}
    return (navigator.language || 'en').toLowerCase().startsWith('es') ? 'es' : 'en';
  }
  let lang = pick();
  document.documentElement.lang = lang;

  window.LANG = () => lang;
  window.t = (key, vars) => {
    let s = D[lang][key] ?? D.en[key] ?? key;
    if (vars) for (const k in vars) s = s.split('{' + k + '}').join(vars[k]);
    return s;
  };
  window.setLang = l => {
    try { localStorage.setItem(KEY, l); } catch (e) {}
    const u = new URL(location.href); u.searchParams.delete('lang');
    location.replace(u.toString());           // se recarga: el estado vive en el PC, no se pierde nada
  };

  function apply() {
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAria)); });
    document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.dataset.ph = t(el.dataset.i18nPh); });
    document.querySelectorAll('[data-lang-switch]').forEach(box => {
      box.innerHTML = '';
      ['es', 'en'].forEach(l => {
        const b = document.createElement('button');
        b.type = 'button'; b.textContent = l.toUpperCase(); b.className = l === lang ? 'on' : '';
        b.setAttribute('aria-pressed', l === lang); b.setAttribute('lang', l);
        b.addEventListener('click', () => { if (l !== lang) setLang(l); });
        box.appendChild(b);
      });
    });
  }
  window.applyI18n = apply;
  apply();   // este archivo se carga al final de la página: el HTML ya existe
})();
