import * as React from "react"

const DropdownMenu = ({ children }) => {
  return <div className="relative inline-block">{children}</div>
}

const DropdownMenuTrigger = ({ children, asChild, ...props }) => {
  return <div {...props}>{children}</div>
}

const DropdownMenuContent = ({ children, align = "end", className = "", ...props }) => {
  const alignClass = align === "end" ? "right-0" : "left-0"
  
  return (
    <div 
      className={`absolute ${alignClass} mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

const DropdownMenuItem = ({ children, className = "", onClick, ...props }) => {
  return (
    <button
      className={`flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  )
}

const DropdownMenuSeparator = ({ className = "", ...props }) => {
  return <div className={`my-1 border-t border-gray-100 ${className}`} {...props} />
}

const DropdownMenuLabel = ({ children, className = "", ...props }) => {
  return (
    <div className={`px-4 py-2 text-sm font-semibold text-gray-900 ${className}`} {...props}>
      {children}
    </div>
  )
}

export {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
}
