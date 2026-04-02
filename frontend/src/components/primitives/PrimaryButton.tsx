import React from 'react';
import { Button, type ButtonProps } from '../ui';

export function PrimaryButton(props: ButtonProps) {
  return <Button variant="primary" {...props} />;
}

