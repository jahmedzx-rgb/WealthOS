import Select, {
  type StylesConfig,
} from 'react-select'
import './LookupSelect.css'

export type LookupOption = {
  value: string
  label: string
}

type LookupSelectProps = {
  label: string
  value: string
  options: LookupOption[]
  placeholder?: string
  disabled?: boolean
  searchable?: boolean
  onChange: (value: string) => void
}

const styles: StylesConfig<LookupOption, false> =
  {
    control: (base, state) => ({
      ...base,
      minHeight: 42,
      height: 42,
      borderRadius: 8,
      borderColor: state.isFocused
        ? '#b79542'
        : 'var(--border-primary)',
      backgroundColor: 'var(--surface-primary)',
      boxShadow: state.isFocused
        ? '0 0 0 2px rgba(183,149,66,.1)'
        : 'none',
      '&:hover': {
        borderColor: state.isFocused
          ? '#b79542'
          : 'var(--border-primary)',
      },
    }),

    valueContainer: (base) => ({
      ...base,
      padding: '0 10px',
      fontSize: 'var(--operation-control-font-size, .875rem)',
    }),

    input: (base) => ({
      ...base,
      margin: 0,
      padding: 0,
      color: 'var(--text-primary)',
      fontSize: 'var(--operation-control-font-size, .875rem)',
    }),

    placeholder: (base) => ({
      ...base,
      color: 'var(--text-muted)',
      fontSize: 'var(--operation-control-font-size, .875rem)',
    }),

    singleValue: (base) => ({
      ...base,
      color: 'var(--text-primary)',
      fontSize: 'var(--operation-control-font-size, .875rem)',
    }),

    indicatorSeparator: () => ({
      display: 'none',
    }),

    dropdownIndicator: (base) => ({
      ...base,
      padding: '0 10px',
      color: 'var(--text-muted)',
    }),

    menu: (base) => ({
      ...base,
      marginTop: 6,
      overflow: 'hidden',
      border: '1px solid var(--border-primary)',
      borderRadius: 10,
      backgroundColor: 'var(--surface-primary)',
      boxShadow: '0 14px 35px rgba(16,41,71,.16)',
      zIndex: 9999,
    }),

    option: (base, state) => ({
      ...base,
      backgroundColor: state.isFocused
        ? 'var(--surface-secondary)'
        : 'var(--surface-primary)',
      color: 'var(--text-primary)',
      cursor: 'pointer',
      fontSize: '.75rem',
    }),
  }

export default function LookupSelect({
  label,
  value,
  options,
  placeholder = 'Select...',
  disabled = false,
  searchable = true,
  onChange,
}: LookupSelectProps) {
  const selected =
    options.find(
      (option) => option.value === value,
    ) ?? null

  return (
    <div className="lookup-select">
      <label>{label}</label>

      <Select<LookupOption, false>
        options={options}
        value={selected}
        placeholder={placeholder}
        isDisabled={disabled}
        isSearchable={searchable}
        styles={styles}
        onChange={(option) =>
          onChange(option?.value ?? '')
        }
      />
    </div>
  )
}
