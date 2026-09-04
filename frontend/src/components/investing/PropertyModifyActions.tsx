import { Link } from 'react-router-dom'
import './PropertyModifyActions.css'

type Props={propertyId:number}

export default function PropertyModifyActions({propertyId}:Props){
  return <span className="module-page__modify-actions module-page__property-actions">
    <Link className="module-page__row-edit" to={`/operations/property?edit=${propertyId}`}>Edit</Link>
    <Link className="module-page__row-edit is-disposition" to={`/operations/sell-asset?property=${propertyId}`}>Sell</Link>
  </span>
}
