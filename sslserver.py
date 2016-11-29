import asyncio

origClass = type(asyncio.get_event_loop())

class MyLoop(origClass):
    def _accept_connection(self, protocol_factory, sock,
                           sslcontext=None, server=None):
        try:
            conn, addr = sock.accept()
            if self._debug:
                logger.debug("%r got a new connection from %r: %r",
                             server, addr, conn)
            conn.setblocking(False)
        except (BlockingIOError, InterruptedError, ConnectionAbortedError):
            pass  # False alarm.
        except OSError as exc:
            # There's nowhere to send the error, so just log it.
            if exc.errno in (errno.EMFILE, errno.ENFILE,
                             errno.ENOBUFS, errno.ENOMEM):
                # Some platforms (e.g. Linux keep reporting the FD as
                # ready, so we remove the read handler temporarily.
                # We'll try again in a while.
                self.call_exception_handler({
                    'message': 'socket.accept() out of system resource',
                    'exception': exc,
                    'socket': sock,
                })
                self.remove_reader(sock.fileno())
                self.call_later(constants.ACCEPT_RETRY_DELAY,
                                self._start_serving,
                                protocol_factory, sock, sslcontext, server)
            else:
                raise  # The event loop will catch, log and ignore it.
        else:
            extra = {'peername': addr}
            if getattr(self, 'ssl_generator') is not None and sslcontext is None:
                sslcontext = self.ssl_generator(conn)
            accept = self._accept_connection2(protocol_factory, conn, extra,
                                              sslcontext, server)
            self.create_task(accept)