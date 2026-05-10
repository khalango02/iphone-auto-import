# iphone-auto-import

Daemon para macOS que importa automaticamente fotos e vídeos do iPhone para o **Photos.app** sempre que o dispositivo é conectado via USB — e, opcionalmente, apaga os arquivos do iPhone após a importação.

## Como funciona

1. O daemon fica em segundo plano verificando a cada 5 segundos se há um iPhone conectado (via protocolo AFC/lockdown — sem precisar de kernel extension).
2. Ao detectar o dispositivo, lista todos os arquivos de mídia na pasta `/DCIM`.
3. Compara com um log local (`~/.iphone_imported.json`) e baixa apenas os arquivos **novos**.
4. Importa cada arquivo para o **Photos.app** via AppleScript.
5. Se `DELETE_AFTER_IMPORT = True`, apaga o arquivo do iPhone após a importação bem-sucedida.
6. O daemon é gerenciado pelo **launchd**: inicia automaticamente no login e reinicia se travar.

## Requisitos

- macOS 12 ou superior
- Python 3.10+
- iPhone pareado com o Mac (é necessário tocar "Confiar" na primeira conexão)
- [Homebrew](https://brew.sh) (opcional, mas recomendado)

## Instalação

```bash
git clone https://github.com/khalango02/iphone-auto-import.git
cd iphone-auto-import
bash setup.sh
```

O script `setup.sh` irá:
- Criar um virtualenv Python em `./venv/`
- Instalar a dependência `pymobiledevice3`
- Registrar e iniciar o daemon via `launchctl`

## Configuração

Edite as constantes no topo do arquivo `iphone_import.py`:

| Variável | Padrão | Descrição |
|---|---|---|
| `DELETE_AFTER_IMPORT` | `True` | Apaga o arquivo do iPhone após importar com sucesso |
| `POLL_INTERVAL` | `5` | Segundos entre cada verificação de dispositivo |
| `MEDIA_EXTENSIONS` | `.jpg .heic .mp4 .mov …` | Extensões de arquivo importadas |

## Uso

```bash
# Ver logs em tempo real
tail -f ~/iphone-import/iphone_import.log

# Parar o daemon
launchctl unload ~/Library/LaunchAgents/com.user.iphone-import.plist

# Iniciar o daemon
launchctl load ~/Library/LaunchAgents/com.user.iphone-import.plist

# Reinstalar após mudanças no script
bash setup.sh
```

## Primeira conexão

Na primeira vez que conectar o iPhone:
1. Desbloqueie o iPhone
2. Toque em **"Confiar neste computador"** quando solicitado
3. O Photos.app abrirá automaticamente durante a importação

Após confiar no Mac, o iPhone pode estar com a tela travada nas conexões seguintes.

## Estrutura

```
iphone-import/
├── iphone_import.py   # Daemon principal
├── setup.sh           # Script de instalação
├── README.md
└── venv/              # Criado pelo setup.sh (não versionado)

~/Library/LaunchAgents/
└── com.user.iphone-import.plist   # Criado pelo setup.sh

~/.iphone_imported.json            # Log de arquivos já importados
```

## Dependências

- [`pymobiledevice3`](https://github.com/doronz88/pymobiledevice3) — comunicação com dispositivos iOS sem kernel extension
- `osascript` — controle do Photos.app via AppleScript (nativo do macOS)

## Notas

- Arquivos **nunca são apagados do iPhone** se a importação para o Photos.app falhar.
- O log `~/.iphone_imported.json` rastreia arquivos pelo caminho no dispositivo. Para reimportar tudo, delete esse arquivo.
- Vídeos grandes são carregados inteiramente em memória durante a transferência; conexões lentas ou vídeos de horas podem demorar.
