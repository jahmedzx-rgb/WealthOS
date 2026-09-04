const storageKey='wealthos-recent-searches'

export function getRecentSearches():string[]{
  try{const value=JSON.parse(localStorage.getItem(storageKey)??'[]');return Array.isArray(value)?value.filter(item=>typeof item==='string'&&item.trim()).slice(0,3):[]}catch{return[]}
}

export function addRecentSearch(value:string):string[]{
  const query=value.trim();if(!query)return getRecentSearches()
  const next=[query,...getRecentSearches().filter(item=>item.toLocaleLowerCase()!==query.toLocaleLowerCase())].slice(0,3)
  localStorage.setItem(storageKey,JSON.stringify(next));return next
}

export function clearRecentSearches(){localStorage.removeItem(storageKey)}
