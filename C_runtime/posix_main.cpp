/*
 * Beremiz C++ runtime
 *
 * This file implements Beremiz C++ runtime Command Line Interface for POSIX
 *
 * Based on erpcsniffer.cpp, BSD-3-Clause, Copyright 2017 NXP
 *
 * Copyright 2024 Beremiz SAS
 * 
 * See COPYING for licensing details
 */

#include <stdlib.h>
#include <vector>
#include <filesystem>

// eRPC includes
#include "erpc_basic_codec.hpp"
#include "erpc_serial_transport.hpp"
#include "erpc_tcp_transport.hpp"
#include "erpc_simple_server.hpp"

// eRPC generated includes
#include "erpc_PLCObject_server.hpp"

// erpcgen includes (re-uses erpcgen's logging system and options parser)
#include "Logging.hpp"
#include "options.hpp"

#include "PLCObject.hpp"

using namespace erpc;
using namespace std;

#define MSG_SIZE 1024*6
class MyMessageBufferFactory : public MessageBufferFactory
{
public:
    virtual MessageBuffer create()
    {
        uint8_t *buf = new uint8_t[MSG_SIZE];
        return MessageBuffer(buf, MSG_SIZE);
    }

    virtual void dispose(MessageBuffer *buf)
    {
        erpc_assert(buf);
        if (*buf)
        {
            delete[] buf->get();
        }
    }
};


namespace beremizRuntime {

/*! The tool's name. */
const char k_toolName[] = "beremizRuntime";

/*! Current version number for the tool. */
const char k_version[] = __STRING(BEREMIZ_VERSION);

/*! Copyright string. */
const char k_copyright[] = "Copyright 2024 Beremiz SAS. All rights reserved.";

static const char *k_optionsDefinition[] = { "?|help",
                                             "V|version",
                                             "v|verbose",
                                             "t:transport <transport>",
                                             "b:baudrate <baudrate>",
                                             "p:port <port>",
                                             "h:host <host>",
                                             "a|autoload",
                                             NULL };

/*! Help string. */
const char k_usageText[] =
    "\nOptions:\n\
  -?/--help                    Show this help\n\
  -V/--version                 Display tool version\n\
  -v/--verbose                 Print extra detailed log information\n\
  -t/--transport <transport>   Type of transport.\n\
  -b/--baudrate <baudrate>     Baud rate.\n\
  -p/--port <port>             Port name or port number.\n\
  -h/--host <host>             Host definition.\n\
  -a/--autoload                Autoload.\n\
\n\
Available transports (use with -t option):\n\
  tcp      Tcp transport type (host, port number).\n\
  serial   Serial transport type (port name, baud rate).\n\
\n";


/*!
 * @brief Class that encapsulates the beremizRuntime tool.
 *
 * A single global logger instance is created during object construction. It is
 * never freed because we need it up to the last possible minute, when an
 * exception could be thrown.
 */
class beremizRuntimeCLI
{
protected:
    enum class verbose_type_t
    {
        kWarning,
        kInfo,
        kDebug,
        kExtraDebug
    }; /*!< Types of verbose outputs from beremizRuntime application. */

    enum class transports_t
    {
        kNoneTransport,
        kTcpTransport,
        kSerialTransport
    }; /*!< Type of transport to use. */

    typedef vector<string> string_vector_t;

    int m_argc;                   /*!< Number of command line arguments. */
    char **m_argv;                /*!< String value for each command line argument. */
    StdoutLogger *m_logger;       /*!< Singleton logger instance. */
    verbose_type_t m_verboseType; /*!< Which type of log is need to set (warning, info, debug). */
    const char *m_workingDir;     /*!< working directory. */
    string_vector_t m_positionalArgs;
    transports_t m_transport; /*!< Transport used for receiving messages. */
    uint32_t m_baudrate;      /*!< Baudrate rate speed. */
    const char *m_port;       /*!< Name or number of port. Based on used transport. */
    const char *m_host;       /*!< Host name */
    bool m_autoload = false;          /*!< Autoload flag. */

public:
    /*!
     * @brief Constructor.
     *
     * @param[in] argc Count of arguments in argv variable.
     * @param[in] argv Pointer to array of arguments.
     *
     * Creates the singleton logger instance.
     */
    beremizRuntimeCLI(int argc, char *argv[]) :
    m_argc(argc), m_argv(argv), m_logger(0), m_verboseType(verbose_type_t::kWarning),
    m_workingDir(NULL), m_transport(transports_t::kNoneTransport), m_baudrate(115200), m_port(NULL),
    m_host(NULL)
    {
        // create logger instance
        m_logger = new StdoutLogger();
        m_logger->setFilterLevel(Logger::log_level_t::kWarning);
        Log::setLogger(m_logger);
    }

    /*!
     * @brief Destructor.
     */
    ~beremizRuntimeCLI() {}

    /*!
     * @brief Reads the command line options passed into the constructor.
     *
     * This method can return a return code to its caller, which will cause the
     * tool to exit immediately with that return code value. Normally, though, it
     * will return -1 to signal that the tool should continue to execute and
     * all options were processed successfully.
     *
     * The Options class is used to parse command line options. See
     * #k_optionsDefinition for the list of options and #k_usageText for the
     * descriptive help for each option.
     *
     * @retval -1 The options were processed successfully. Let the tool run normally.
     * @return A zero or positive result is a return code value that should be
     *      returned from the tool as it exits immediately.
     */
    int processOptions()
    {
        Options options(*m_argv, k_optionsDefinition);
        OptArgvIter iter(--m_argc, ++m_argv);

        // process command line options
        int optchar;
        const char *optarg;
        while ((optchar = options(iter, optarg)))
        {
            switch (optchar)
            {
                case '?':
                {
                    printUsage(options);
                    return 0;
                }

                case 'V':
                {
                    printf("%s %s\n%s\n", k_toolName, k_version, k_copyright);
                    return 0;
                }

                case 'v':
                {
                    if (m_verboseType != verbose_type_t::kExtraDebug)
                    {
                        m_verboseType = (verbose_type_t)(((int)m_verboseType) + 1);
                    }
                    break;
                }

                case 't':
                {
                    string transport = optarg;
                    if (transport == "tcp")
                    {
                        m_transport = transports_t::kTcpTransport;
                    }
                    else if (transport == "serial")
                    {
                        m_transport = transports_t::kSerialTransport;
                    }
                    else
                    {
                        Log::error("error: unknown transport type %s", transport.c_str());
                        return 1;
                    }
                    break;
                }

                case 'b':
                {
                    m_baudrate = strtoul(optarg, NULL, 10);
                    break;
                }

                case 'p':
                {
                    m_port = optarg;
                    break;
                }

                case 'h':
                {
                    m_host = optarg;
                    break;
                }

                case 'a':
                {
                    m_autoload = true;
                    break;
                }

                default:
                {
                    Log::error("error: unrecognized option\n\n");
                    printUsage(options);
                    return 0;
                }
            }
        }

        // handle positional args
        if (iter.index() < m_argc)
        {
            if (m_argc - iter.index() > 1){
                Log::error("error: too many arguments\n\n");
                printUsage(options);
                return 0;
            }
            int i;
            for (i = iter.index(); i < m_argc; ++i)
            {
                m_positionalArgs.push_back(m_argv[i]);
            }
        }

        // all is well
        return -1;
    }

    /*!
     * @brief Prints help for the tool.
     *
     * @param[in] options Options, which can be used.
     */
    void printUsage(Options &options)
    {
        options.usage(cout, "[path]");
        printf(k_usageText);
    }

    /*!
     * @brief Core of the tool.
     *
     * Calls processOptions() to handle command line options before performing the
     * real work the tool does.
     *
     * @retval 1 The functions wasn't processed successfully.
     * @retval 0 The function was processed successfully.
     *
     * @exception Log::error This function is called, when function wasn't
     *              processed successfully.
     * @exception runtime_error Thrown, when positional args is empty.
     */
    int run()
    {
        try
        {
            // read command line options
            int result;
            if ((result = processOptions()) != -1)
            {
                return result;
            }

            // set verbose logging
            setVerboseLogging();

            if (!m_positionalArgs.size())
            {
                m_workingDir = std::filesystem::current_path().c_str();
            } else {
                m_workingDir = m_positionalArgs[0].c_str();
                std::filesystem::current_path(m_workingDir);
            }

            // remove temporary directory if it already exists
            if (std::filesystem::exists("tmp"))
            {
                std::filesystem::remove_all("tmp");
            }

            // Create temporary directory in working directory
            std::filesystem::create_directory("tmp");

            Transport *_transport;
            switch (m_transport)
            {
                case transports_t::kTcpTransport:
                {
                    uint16_t portNumber = strtoul(m_port, NULL, 10);
                    TCPTransport *tcpTransport = new TCPTransport(m_host, portNumber, true);
                    if (erpc_status_t err = tcpTransport->open())
                    {
                        return err;
                    }
                    _transport = tcpTransport;
                    break;
                }

                case transports_t::kSerialTransport:
                {
                    SerialTransport *serialTransport = new SerialTransport(m_port, m_baudrate);

                    uint8_t vtime = 0;
                    uint8_t vmin = 1;
                    while (kErpcStatus_Success != serialTransport->init(vtime, vmin))
                        ;

                    _transport = serialTransport;
                    break;
                }

                default:
                {
                    break;
                }
            }

            Crc16 crc;
            _transport->setCrc16(&crc);

            MyMessageBufferFactory _msgFactory;
            BasicCodecFactory _basicCodecFactory;
            SimpleServer _server;

            Log::info("Starting ERPC server...\n");

            _server.setMessageBufferFactory(&_msgFactory);
            _server.setTransport(_transport);
            _server.setCodecFactory(&_basicCodecFactory);

            PLCObject plc_object = PLCObject();
            BeremizPLCObjectService_service svc = BeremizPLCObjectService_service(&plc_object);

            _server.addService(&svc);

            if(m_autoload)
            {
                plc_object.AutoLoad();
            }

            _server.run();

            return 0;
        }
        catch (exception &e)
        {
            Log::error("error: %s\n", e.what());
            return 1;
        }
        catch (...)
        {
            Log::error("error: unexpected exception\n");
            return 1;
        }

        return 0;
    }

    /*!
     * @brief Turns on verbose logging.
     */
    void setVerboseLogging()
    {
        // verbose only affects the INFO and DEBUG filter levels
        // if the user has selected quiet mode, it overrides verbose
        switch (m_verboseType)
        {
            case verbose_type_t::kWarning:
                Log::getLogger()->setFilterLevel(Logger::log_level_t::kWarning);
                break;
            case verbose_type_t::kInfo:
                Log::getLogger()->setFilterLevel(Logger::log_level_t::kInfo);
                break;
            case verbose_type_t::kDebug:
                Log::getLogger()->setFilterLevel(Logger::log_level_t::kDebug);
                break;
            case verbose_type_t::kExtraDebug:
                Log::getLogger()->setFilterLevel(Logger::log_level_t::kDebug2);
                break;
        }
    }
};

} // namespace beremizRuntime

/*!
 * @brief Main application entry point.
 *
 * Creates a tool instance and lets it take over.
 */
int main(int argc, char *argv[], char *envp[])
{
    (void)envp;
    try
    {
        return beremizRuntime::beremizRuntimeCLI(argc, argv).run();
    }
    catch (...)
    {
        Log::error("error: unexpected exception\n");
        return 1;
    }

    return 0;
}