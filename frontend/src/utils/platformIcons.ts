const platformIconUrls: Record<string, string> = {
  AFAQ: '/platforms/afaq.ico',
  ABYAN: '/platforms/abyan.png',
  CIRCLES: '/platforms/circlys.svg',
  DINAR: '/platforms/dinar.png',
  HAKBAH: '/platforms/hakbah.png',
  IDIKHAR: '/platforms/idikhar.svg',
  MALAA: '/platforms/malaa.ico',
  MANAFA: '/platforms/manafa.png',
  SAFQAH: '/platforms/safqah.png',
  STAKE: '/platforms/stake.png',
  SUKUK: '/platforms/sukuk.ico',
  TAMRA: '/platforms/tamra.ico',
  TARMEEZ: '/platforms/tarmeez.png',
}

export const getPlatformIconUrl = (code: string) => platformIconUrls[code]
