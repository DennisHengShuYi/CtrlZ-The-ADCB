import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    isLoading?: boolean;
    variant?: "primary" | "secondary" | "danger" | "icon";
    icon?: React.ReactNode;
}

export function Button({
    children,
    isLoading,
    variant = "primary",
    icon,
    className = "",
    disabled,
    ...props
}: ButtonProps) {
    let baseClass = "";
    if (variant === "primary") baseClass = "btn btn-primary";
    if (variant === "secondary") baseClass = "btn btn-secondary";
    if (variant === "danger") baseClass = "btn btn-danger text-white bg-red-600 hover:bg-red-700";
    if (variant === "icon") baseClass = "btn-icon";

    return (
        <button
            className={`${baseClass} flex items-center justify-center gap-2 ${className}`}
            disabled={isLoading || disabled}
            {...props}
        >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : icon}
            {children}
        </button>
    );
}
