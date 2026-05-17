import {
  Box,
  Button,
  chakra,
  CircularProgress,
  FormControl,
  FormErrorMessage,
  FormLabel,
  HStack,
  IconButton,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Textarea,
  Th,
  Thead,
  Tooltip,
  Tr,
  useToast,
  VStack,
} from "@chakra-ui/react";
import {
  AdjustmentsHorizontalIcon,
  CheckIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { usePanelSettings } from "contexts/SettingsContext";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Setting, SettingValue } from "types/Setting";
import { Icon } from "./Icon";

const HeaderIcon = chakra(AdjustmentsHorizontalIcon, {
  baseStyle: { w: 5, h: 5 },
});
const EditIcon = chakra(PencilSquareIcon, { baseStyle: { w: 4, h: 4 } });
const DeleteIcon = chakra(TrashIcon, { baseStyle: { w: 4, h: 4 } });
const SaveIcon = chakra(CheckIcon, { baseStyle: { w: 4, h: 4 } });
const CancelIcon = chakra(XMarkIcon, { baseStyle: { w: 4, h: 4 } });

const formatValue = (value: SettingValue): string => {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
};

const parseValue = (input: string): SettingValue => {
  const trimmed = input.trim();
  if (trimmed === "") return "";
  try {
    return JSON.parse(trimmed) as SettingValue;
  } catch {
    return input;
  }
};

type RowProps = {
  setting: Setting;
  onSave: (key: string, value: SettingValue) => Promise<unknown>;
  onDelete: (key: string) => Promise<void>;
  busy: boolean;
};

const SettingRow: FC<RowProps> = ({ setting, onSave, onDelete, busy }) => {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<string>(formatValue(setting.value));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(formatValue(setting.value));
  }, [setting.value, editing]);

  const startEdit = () => {
    setDraft(formatValue(setting.value));
    setError(null);
    setEditing(true);
  };

  const cancelEdit = () => {
    setError(null);
    setEditing(false);
  };

  const submit = () => {
    const next = parseValue(draft);
    setError(null);
    onSave(setting.key, next)
      .then(() => setEditing(false))
      .catch((e) => setError(e?.message || String(e)));
  };

  return (
    <Tr>
      <Td verticalAlign="top" fontFamily="mono" fontSize="sm" maxW="220px" wordBreak="break-all">
        {setting.key}
      </Td>
      <Td verticalAlign="top">
        {editing ? (
          <FormControl isInvalid={!!error}>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              fontFamily="mono"
              fontSize="sm"
              rows={Math.min(8, Math.max(2, draft.split("\n").length))}
            />
            {error && <FormErrorMessage>{error}</FormErrorMessage>}
            <Text mt={1} fontSize="xs" opacity={0.6}>
              {t("panelSettings.valueHint")}
            </Text>
          </FormControl>
        ) : (
          <Box
            as="pre"
            fontFamily="mono"
            fontSize="sm"
            whiteSpace="pre-wrap"
            wordBreak="break-all"
            m={0}
          >
            {formatValue(setting.value)}
          </Box>
        )}
      </Td>
      <Td verticalAlign="top" textAlign="right" whiteSpace="nowrap">
        {editing ? (
          <HStack justify="flex-end" spacing={1}>
            <Tooltip label={t("panelSettings.save")}>
              <IconButton
                size="sm"
                aria-label="save"
                icon={<SaveIcon />}
                onClick={submit}
                isDisabled={busy}
                colorScheme="primary"
              />
            </Tooltip>
            <Tooltip label={t("panelSettings.cancel")}>
              <IconButton
                size="sm"
                aria-label="cancel"
                icon={<CancelIcon />}
                onClick={cancelEdit}
                isDisabled={busy}
                variant="outline"
              />
            </Tooltip>
          </HStack>
        ) : (
          <HStack justify="flex-end" spacing={1}>
            <Tooltip label={t("panelSettings.edit")}>
              <IconButton
                size="sm"
                aria-label="edit"
                icon={<EditIcon />}
                onClick={startEdit}
                isDisabled={busy}
                variant="outline"
              />
            </Tooltip>
            <Tooltip label={t("panelSettings.delete")}>
              <IconButton
                size="sm"
                aria-label="delete"
                icon={<DeleteIcon />}
                onClick={() => onDelete(setting.key)}
                isDisabled={busy}
                colorScheme="red"
                variant="outline"
              />
            </Tooltip>
          </HStack>
        )}
      </Td>
    </Tr>
  );
};

const AddSettingForm: FC<{
  busy: boolean;
  existingKeys: string[];
  onAdd: (key: string, value: SettingValue) => Promise<unknown>;
}> = ({ busy, existingKeys, onAdd }) => {
  const { t } = useTranslation();
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    const trimmedKey = key.trim();
    if (!trimmedKey) {
      setError(t("panelSettings.errorEmptyKey"));
      return;
    }
    if (existingKeys.includes(trimmedKey)) {
      setError(t("panelSettings.errorDuplicateKey"));
      return;
    }
    const parsed = parseValue(value);
    setError(null);
    onAdd(trimmedKey, parsed)
      .then(() => {
        setKey("");
        setValue("");
      })
      .catch((e) => setError(e?.message || String(e)));
  };

  return (
    <VStack align="stretch" spacing={2} mt={4}>
      <Text fontWeight="semibold" fontSize="sm">
        {t("panelSettings.addNew")}
      </Text>
      <HStack align="flex-start" spacing={2}>
        <FormControl isInvalid={!!error} flex="0 0 220px">
          <FormLabel fontSize="xs">{t("panelSettings.key")}</FormLabel>
          <Input
            size="sm"
            value={key}
            placeholder="SUB_ANNOUNCE"
            onChange={(e) => setKey(e.target.value)}
            fontFamily="mono"
          />
        </FormControl>
        <FormControl flex="1" isInvalid={!!error}>
          <FormLabel fontSize="xs">{t("panelSettings.value")}</FormLabel>
          <Textarea
            size="sm"
            value={value}
            placeholder='"text" / ["a","b"] / 42 / true'
            onChange={(e) => setValue(e.target.value)}
            fontFamily="mono"
            rows={2}
          />
          {error && <FormErrorMessage>{error}</FormErrorMessage>}
        </FormControl>
      </HStack>
      <HStack justify="flex-end">
        <Button size="sm" onClick={submit} isDisabled={busy} colorScheme="primary">
          {t("panelSettings.add")}
        </Button>
      </HStack>
      <Text fontSize="xs" opacity={0.6}>
        {t("panelSettings.valueHint")}
      </Text>
    </VStack>
  );
};

const PanelSettingsContent: FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const { settings, isLoading, isPostLoading, fetchSettings, setSetting, deleteSetting } =
    usePanelSettings();
  const { isEditingPanelSettings } = useDashboard();

  useEffect(() => {
    if (isEditingPanelSettings) fetchSettings();
  }, [isEditingPanelSettings]);

  const existingKeys = useMemo(() => settings.map((s) => s.key), [settings]);

  const showError = (e: any) => {
    const detail = e?.response?._data?.detail;
    const msg = typeof detail === "string" ? detail : e?.message || String(e);
    toast({ title: msg, status: "error", isClosable: true, position: "top", duration: 3000 });
    throw e;
  };

  const handleSave = (key: string, value: SettingValue) =>
    setSetting(key, value)
      .then(() =>
        toast({
          title: t("panelSettings.saved"),
          status: "success",
          isClosable: true,
          position: "top",
          duration: 2000,
        })
      )
      .catch(showError);

  const handleDelete = (key: string): Promise<void> =>
    deleteSetting(key)
      .then(() => {
        toast({
          title: t("panelSettings.deleted"),
          status: "success",
          isClosable: true,
          position: "top",
          duration: 2000,
        });
      })
      .catch(showError);

  return (
    <>
      <ModalBody>
        <Text fontSize="sm" opacity={0.7} mb={3}>
          {t("panelSettings.description")}
        </Text>
        {isLoading ? (
          <HStack justify="center" py={6}>
            <CircularProgress isIndeterminate size="20px" />
          </HStack>
        ) : settings.length === 0 ? (
          <Text fontSize="sm" opacity={0.6} py={4} textAlign="center">
            {t("panelSettings.empty")}
          </Text>
        ) : (
          <TableContainer>
            <Table size="sm">
              <Thead>
                <Tr>
                  <Th>{t("panelSettings.key")}</Th>
                  <Th>{t("panelSettings.value")}</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {settings.map((s) => (
                  <SettingRow
                    key={s.key}
                    setting={s}
                    onSave={handleSave}
                    onDelete={handleDelete}
                    busy={isPostLoading}
                  />
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        )}
        <AddSettingForm busy={isPostLoading} existingKeys={existingKeys} onAdd={handleSave} />
      </ModalBody>
      <ModalFooter />
    </>
  );
};

export const PanelSettingsDialog: FC = () => {
  const { t } = useTranslation();
  const { isEditingPanelSettings, onEditingPanelSettings } = useDashboard();

  return (
    <Modal
      isOpen={isEditingPanelSettings}
      onClose={() => onEditingPanelSettings(false)}
      size="3xl"
    >
      <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
      <ModalContent mx="3" w="full">
        <ModalHeader pt={6}>
          <HStack gap={2}>
            <Icon color="primary">
              <HeaderIcon color="white" />
            </Icon>
            <Text fontWeight="semibold" fontSize="lg">
              {t("panelSettings.title")}
            </Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton mt={3} />
        <PanelSettingsContent />
      </ModalContent>
    </Modal>
  );
};
