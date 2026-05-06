"use client";

import React from "react";
import { motion, HTMLMotionProps } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export interface ButtonProps extends HTMLMotionProps<"button"> {
    variant?: "primary" | "secondary" | "outline" | "ghost";
    size?: "sm" | "md" | "lg";
    children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "primary", size = "md", children, ...props }, ref) => {

        const variants = {
            primary: "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md hover:shadow-lg hover:from-blue-700 hover:to-indigo-700",
            secondary: "bg-white/5 backdrop-blur-md border border-white/20 text-white hover:bg-white/10 shadow-sm transition-colors",
            outline: "bg-transparent border-2 border-slate-600 text-slate-300 hover:border-slate-400 hover:text-white transition-colors",
            ghost: "bg-transparent text-slate-400 hover:bg-white/10 hover:text-white transition-colors"
        };

        const sizes = {
            sm: "h-9 px-4 text-sm",
            md: "h-11 px-6 text-base",
            lg: "h-14 px-8 text-lg font-medium",
        };

        return (
            <motion.button
                ref={ref}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={cn(
                    "inline-flex items-center justify-center rounded-full font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:pointer-events-none disabled:opacity-50",
                    variants[variant],
                    sizes[size],
                    className
                )}
                {...props}
            >
                {children}
            </motion.button>
        );
    }
);

Button.displayName = "Button";
