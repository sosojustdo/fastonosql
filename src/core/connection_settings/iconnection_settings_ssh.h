/*  Copyright (C) 2014-2016 FastoGT. All right reserved.

    This file is part of FastoNoSQL.

    FastoNoSQL is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    FastoNoSQL is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with FastoNoSQL.  If not, see <http://www.gnu.org/licenses/>.
*/

#pragma once

#include "core/ssh_info.h"  // for SSHInfo

#include "core/connection_settings/iconnection_settings_remote.h"

namespace fastonosql {
namespace core {

class IConnectionSettingsRemoteSSH : public IConnectionSettingsRemote {
 public:
  virtual std::string Delimiter() const = 0;
  virtual void SetDelimiter(const std::string& delimiter) = 0;

  virtual std::string NsSeparator() const = 0;
  virtual void SetNsSeparator(const std::string& ns) = 0;

  virtual common::net::HostAndPort Host() const = 0;
  virtual void SetHost(const common::net::HostAndPort& host) = 0;

  virtual std::string CommandLine() const = 0;
  virtual void SetCommandLine(const std::string& line) = 0;

  struct SSHInfo SSHInfo() const;
  void SetSSHInfo(const struct SSHInfo& info);

  virtual std::string ToString() const override;

 protected:
  IConnectionSettingsRemoteSSH(const connection_path_t& connectionName, connectionTypes type);

 private:
  struct SSHInfo ssh_info_;
};

}  // namespace core
}  // namespace fastonosql