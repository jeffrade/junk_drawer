#!/bin/bash

set e

if [ ! "$(command -v ruby)" ]; then
  echo "Installing ruby..."
  sudo apt update && sudo apt install ruby-full
fi

if [ ! "$(command -v bundle)" ]; then
  echo "Installing bundler..."
  echo "PATH=\$HOME/.gem/ruby/2.7.0/bin:\$HOME/.gem/ruby/3.0.0/bin:\$HOME/.gem/ruby/3.2.0/bin:\$PATH" >> "$HOME/.profile"
  # shellcheck source=/dev/null
  source "$HOME/.profile"
  gem install bundler --user-install
fi

if ! grep -q GEM_HOME "$HOME/.profile"; then
  echo "#export GEM_HOME=$HOME/todo/where/is/this" >> "$HOME/.profile"
fi

echo "Make sure to start a new terminal window!"
echo "Done!"
